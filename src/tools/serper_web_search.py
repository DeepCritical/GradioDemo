"""Serper web search tool using Serper API for Google searches."""

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.tools.query_utils import preprocess_query
from src.tools.rate_limiter import get_serper_limiter
from src.tools.vendored.serper_client import SerperClient
from src.tools.vendored.web_search_core import scrape_urls
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError, RateLimitError, SearchError
from src.utils.models import Citation, Evidence

logger = structlog.get_logger()


class SerperWebSearchTool:
    """Tool for searching the web using Serper API (Google search)."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Serper web search tool.

        Args:
            api_key: Serper API key. If None, reads from settings.

        Raises:
            ConfigurationError: If no API key is available.
        """
        self.api_key = api_key or settings.serper_api_key
        if not self.api_key:
            raise ConfigurationError(
                "Serper API key required. Set SERPER_API_KEY environment variable or serper_api_key in settings."
            )

        self._client = SerperClient(api_key=self.api_key)
        self._limiter = get_serper_limiter(self.api_key)

    @property
    def name(self) -> str:
        """Return the name of this search tool."""
        return "serper"

    async def _rate_limit(self) -> None:
        """Enforce Serper API rate limiting."""
        await self._limiter.acquire()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Execute a web search using Serper API.

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
                        source="serper",
                        date="Unknown",
                        authors=[],
                    ),
                    relevance=0.0,
                )
                evidence.append(ev)

            logger.info(
                "Serper search complete",
                query=final_query,
                results_found=len(evidence),
            )

            return evidence

        except RateLimitError:
            raise
        except SearchError:
            raise
        except Exception as e:
            logger.error("Unexpected error in Serper search", error=str(e), query=final_query)
            raise SearchError(f"Serper search failed: {e}") from e










