"""SearchXNG API client for Google searches.

Vendored and adapted from folder/tools/web_search.py.
"""

import os

import aiohttp
import structlog

from src.tools.vendored.web_search_core import WebpageSnippet, ssl_context
from src.utils.exceptions import RateLimitError, SearchError

logger = structlog.get_logger()


class SearchXNGClient:
    """A client for the SearchXNG API to perform Google searches."""

    def __init__(self, host: str | None = None) -> None:
        """Initialize SearchXNG client.

        Args:
            host: SearchXNG host URL. If None, reads from SEARCHXNG_HOST env var.

        Raises:
            ConfigurationError: If no host is provided.
        """
        host = host or os.getenv("SEARCHXNG_HOST")
        if not host:
            from src.utils.exceptions import ConfigurationError

            raise ConfigurationError("SEARCHXNG_HOST environment variable is not set")

        # Ensure host ends with /search
        if not host.endswith("/search"):
            host = f"{host}/search" if not host.endswith("/") else f"{host}search"

        self.host: str = host

    async def search(
        self, query: str, filter_for_relevance: bool = False, max_results: int = 5
    ) -> list[WebpageSnippet]:
        """Perform a search using SearchXNG API.

        Args:
            query: The search query
            filter_for_relevance: Whether to filter results (currently not implemented)
            max_results: Maximum number of results to return

        Returns:
            List of WebpageSnippet objects with search results

        Raises:
            SearchError: If the search fails
            RateLimitError: If rate limit is exceeded
        """
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                params = {
                    "q": query,
                    "format": "json",
                }

                async with session.get(self.host, params=params) as response:
                    if response.status == 429:
                        raise RateLimitError("SearchXNG API rate limit exceeded")

                    response.raise_for_status()
                    results = await response.json()

                    results_list = [
                        WebpageSnippet(
                            url=result.get("url", ""),
                            title=result.get("title", ""),
                            description=result.get("content", ""),
                        )
                        for result in results.get("results", [])
                    ]

                    if not results_list:
                        logger.info("No search results found", query=query)
                        return []

                    # Return results up to max_results
                    return results_list[:max_results]

        except aiohttp.ClientError as e:
            logger.error("SearchXNG API request failed", error=str(e), query=query)
            raise SearchError(f"SearchXNG API request failed: {e}") from e
        except RateLimitError:
            raise
        except Exception as e:
            logger.error("Unexpected error in SearchXNG search", error=str(e), query=query)
            raise SearchError(f"SearchXNG search failed: {e}") from e
