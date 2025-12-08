"""Fallback web search tool that tries Serper first, then DuckDuckGo on errors."""

import structlog

from src.tools.serper_web_search import SerperWebSearchTool
from src.tools.web_search import WebSearchTool
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError, RateLimitError, SearchError
from src.utils.models import Evidence

logger = structlog.get_logger()


class FallbackWebSearchTool:
    """Web search tool that tries Serper first, falls back to DuckDuckGo on any error.
    
    This ensures search always works even if Serper fails due to:
    - Credit exhaustion (403 Forbidden)
    - Rate limiting (429)
    - Network errors
    - Invalid API key
    - Any other errors
    """

    def __init__(self) -> None:
        """Initialize fallback web search tool."""
        self._serper_tool: SerperWebSearchTool | None = None
        self._duckduckgo_tool: WebSearchTool | None = None
        self._serper_available = False
        
        # Try to initialize Serper if API key is available
        if settings.serper_api_key:
            try:
                self._serper_tool = SerperWebSearchTool()
                self._serper_available = True
                logger.info("Serper web search initialized for fallback tool")
            except Exception as e:
                logger.warning(
                    "Failed to initialize Serper, will use DuckDuckGo only",
                    error=str(e),
                )
                self._serper_available = False
        
        # DuckDuckGo is always available as fallback
        self._duckduckgo_tool = WebSearchTool()
        logger.info("DuckDuckGo web search initialized as fallback")

    @property
    def name(self) -> str:
        """Return the name of this search tool."""
        return "serper" if self._serper_available else "duckduckgo"

    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Execute web search with automatic fallback.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of Evidence objects from Serper (if successful) or DuckDuckGo (if fallback)
        """
        # Try Serper first if available
        if self._serper_available and self._serper_tool:
            try:
                logger.debug("Attempting Serper search", query=query)
                results = await self._serper_tool.search(query, max_results=max_results)
                logger.info(
                    "Serper search successful",
                    query=query,
                    results_count=len(results),
                )
                return results
            except (ConfigurationError, RateLimitError, SearchError) as e:
                # Serper failed - log and fall back to DuckDuckGo
                logger.warning(
                    "Serper search failed, falling back to DuckDuckGo",
                    error=str(e),
                    error_type=type(e).__name__,
                    query=query,
                )
                # Mark Serper as unavailable for future requests (optional optimization)
                # self._serper_available = False
            except Exception as e:
                # Unexpected error from Serper - fall back
                logger.error(
                    "Unexpected error in Serper search, falling back to DuckDuckGo",
                    error=str(e),
                    error_type=type(e).__name__,
                    query=query,
                )
        
        # Fall back to DuckDuckGo
        if self._duckduckgo_tool:
            try:
                logger.info("Using DuckDuckGo search", query=query)
                results = await self._duckduckgo_tool.search(query, max_results=max_results)
                logger.info(
                    "DuckDuckGo search successful",
                    query=query,
                    results_count=len(results),
                )
                return results
            except Exception as e:
                logger.error(
                    "DuckDuckGo search also failed",
                    error=str(e),
                    query=query,
                )
                # If even DuckDuckGo fails, return empty list
                return []
        
        # Should never reach here, but just in case
        logger.error("No web search tools available")
        return []


