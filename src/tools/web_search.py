"""Web search tool using DuckDuckGo."""

import asyncio

import structlog
from duckduckgo_search import DDGS

from src.tools.query_utils import preprocess_query
from src.utils.exceptions import SearchError
from src.utils.models import Citation, Evidence

logger = structlog.get_logger()


class WebSearchTool:
    """Tool for searching the web using DuckDuckGo."""

    def __init__(self) -> None:
        self._ddgs = DDGS()

    @property
    def name(self) -> str:
        """Return the name of this search tool."""
        return "duckduckgo"

    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Execute a web search and return evidence.

        Args:
            query: The search query string
            max_results: Maximum number of results to return

        Returns:
            List of Evidence objects

        Raises:
            SearchError: If the search fails
        """
        try:
            # Preprocess query to remove noise
            clean_query = preprocess_query(query)
            final_query = clean_query if clean_query else query

            loop = asyncio.get_running_loop()

            def _do_search() -> list[dict[str, str]]:
                # text() returns an iterator, need to list() it or iterate
                return list(self._ddgs.text(final_query, max_results=max_results))

            raw_results = await loop.run_in_executor(None, _do_search)

            evidence = []
            for r in raw_results:
                ev = Evidence(
                    content=r.get("body", ""),
                    citation=Citation(
                        title=r.get("title", "No Title"),
                        url=r.get("href", ""),
                        source="web",
                        date="Unknown",
                        authors=[],
                    ),
                    relevance=0.0,
                )
                evidence.append(ev)

            return evidence

        except Exception as e:
            logger.error("Web search failed", error=str(e), query=query)
            raise SearchError(f"DuckDuckGo search failed: {e}") from e
