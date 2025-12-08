"""Serper API client for Google searches.

Vendored and adapted from folder/tools/web_search.py.
"""

import os

import aiohttp
import structlog

from src.tools.vendored.web_search_core import WebpageSnippet, ssl_context
from src.utils.exceptions import ConfigurationError, RateLimitError, SearchError

logger = structlog.get_logger()


class SerperClient:
    """A client for the Serper API to perform Google searches."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Serper client.

        Args:
            api_key: Serper API key. If None, reads from SERPER_API_KEY env var.

        Raises:
            ConfigurationError: If no API key is provided.
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            from src.utils.exceptions import ConfigurationError

            raise ConfigurationError(
                "No API key provided. Set SERPER_API_KEY environment variable."
            )

        # Serper API endpoint and headers
        # Documentation: https://serper.dev/api
        # Format: POST https://google.serper.dev/search
        # Headers: X-API-KEY (required), Content-Type: application/json
        # Body: {"q": "search query", "autocorrect": false}
        self.url = "https://google.serper.dev/search"
        self.headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    async def search(
        self, query: str, filter_for_relevance: bool = False, max_results: int = 5
    ) -> list[WebpageSnippet]:
        """Perform a Google search using Serper API.

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
                # Verify API call format matches Serper API documentation:
                # POST https://google.serper.dev/search
                # Headers: X-API-KEY, Content-Type: application/json
                # Body: {"q": query, "autocorrect": false}
                async with session.post(
                    self.url,
                    headers=self.headers,
                    json={"q": query, "autocorrect": False},
                    timeout=aiohttp.ClientTimeout(total=30),  # 30 second timeout
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("Serper API rate limit exceeded")
                    
                    if response.status == 403:
                        # 403 can mean either invalid key OR credits exhausted
                        # For free tier (2,500 credits), it's often credit exhaustion
                        # Read response body to get more details
                        try:
                            error_body = await response.text()
                            logger.warning(
                                "Serper API returned 403 Forbidden",
                                status=403,
                                body=error_body[:200],  # Truncate for logging
                                hint="May be credit exhaustion (free tier: 2,500 credits) or invalid key",
                            )
                        except Exception:
                            pass
                        
                        # Raise RateLimitError instead of ConfigurationError
                        # This allows retry logic to handle credit exhaustion
                        # The retry decorator will use exponential backoff with jitter
                        raise RateLimitError(
                            "Serper API credits may be exhausted (403 Forbidden). "
                            "Free tier provides 2,500 credits (one-time, expire after 6 months). "
                            "Check your dashboard at https://serper.dev/dashboard. "
                            "Retrying with backoff..."
                        )

                    response.raise_for_status()
                    results = await response.json()

                    results_list = [
                        WebpageSnippet(
                            url=result.get("link", ""),
                            title=result.get("title", ""),
                            description=result.get("snippet", ""),
                        )
                        for result in results.get("organic", [])
                    ]

                    if not results_list:
                        logger.info("No search results found", query=query)
                        return []

                    # Return results up to max_results
                    return results_list[:max_results]

        except aiohttp.ClientError as e:
            logger.error("Serper API request failed", error=str(e), query=query)
            raise SearchError(f"Serper API request failed: {e}") from e
        except RateLimitError:
            raise
        except Exception as e:
            logger.error("Unexpected error in Serper search", error=str(e), query=query)
            raise SearchError(f"Serper search failed: {e}") from e










