"""SearchXNG web search tool using SearchXNG API for Google searches."""

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.tools.query_utils import preprocess_query
from src.tools.rate_limiter import get_searchxng_limiter
from src.tools.vendored.searchxng_client import SearchXNGClient
from src.tools.vendored.web_search_core import scrape_urls
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError, RateLimitError, SearchError
from src.utils.models import Citation, Evidence

logger = structlog.get_logger()


class SearchXNGWebSearchTool:
    """Tool for searching the web using SearchXNG API (Google search)."""

    def __init__(self, host: str | None = None) -> None:
        """Initialize SearchXNG web search tool.

        Args:
            host: SearchXNG host URL. If None, reads from settings.

        Raises:
            ConfigurationError: If no host is available.
        """
        self.host = host or settings.searchxng_host
        if not self.host:
            raise ConfigurationError(
                "SearchXNG host required. Set SEARCHXNG_HOST environment variable or searchxng_host in settings."
            )

        self._client = SearchXNGClient(host=self.host)
        self._limiter = get_searchxng_limiter()

    @property
    def name(self) -> str:
        """Return the name of this search tool."""
        return "searchxng"

    async def _rate_limit(self) -> None:
        """Enforce SearchXNG API rate limiting."""
        await self._limiter.acquire()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Execute a web search using SearchXNG API.

        Args:
            query: The search query string
            max_results: Maximum number of results to return

        Returns:
            List of Evidence objects

        Raises:
            SearchError: If the search fails
            RateLimitError: If rate limit is exceeded
        """
        await self._rate_limit()

        # Preprocess query to remove noise
        clean_query = preprocess_query(query)
        final_query = clean_query if clean_query else query

        try:
            # Get search results (snippets)
            search_results = await self._client.search(
                final_query, filter_for_relevance=False, max_results=max_results
            )

            if not search_results:
                logger.info("No search results found", query=final_query)
                return []

            # Scrape URLs to get full content
            scraped = await scrape_urls(search_results)

            # Convert ScrapeResult to Evidence objects
            evidence = []
            for result in scraped:
                ev = Evidence(
                    content=result.text,
                    citation=Citation(
                        title=result.title,
                        url=result.url,
                        source="searchxng",
                        date="Unknown",
                        authors=[],
                    ),
                    relevance=0.0,
                )
                evidence.append(ev)

            logger.info(
                "SearchXNG search complete",
                query=final_query,
                results_found=len(evidence),
            )

            return evidence

        except RateLimitError:
            raise
        except SearchError:
            raise
        except Exception as e:
            logger.error("Unexpected error in SearchXNG search", error=str(e), query=final_query)
            raise SearchError(f"SearchXNG search failed: {e}") from e

