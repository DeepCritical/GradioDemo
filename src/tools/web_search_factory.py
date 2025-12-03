"""Factory for creating web search tools based on configuration."""

import structlog

from src.tools.base import SearchTool
from src.tools.searchxng_web_search import SearchXNGWebSearchTool
from src.tools.serper_web_search import SerperWebSearchTool
from src.tools.web_search import WebSearchTool
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger()


def create_web_search_tool(provider: str | None = None) -> SearchTool | None:
    """Create a web search tool based on configuration.

    Args:
        provider: Override provider selection. If None, uses settings.web_search_provider.

    Returns:
        SearchTool instance, or None if not available/configured

    The tool is selected based on provider (or settings.web_search_provider if None):
    - "serper": SerperWebSearchTool (requires SERPER_API_KEY)
    - "searchxng": SearchXNGWebSearchTool (requires SEARCHXNG_HOST)
    - "duckduckgo": WebSearchTool (always available, no API key)
    - "brave" or "tavily": Not yet implemented, returns None
    - "auto": Auto-detect best available provider (prefers Serper > SearchXNG > DuckDuckGo)

    Auto-detection logic (when provider is "auto" or not explicitly set):
    1. Try Serper if SERPER_API_KEY is available (best quality - Google search + full content scraping)
    2. Try SearchXNG if SEARCHXNG_HOST is available
    3. Fall back to DuckDuckGo (always available, but lower quality - snippets only)
    """
    provider = provider or settings.web_search_provider

    # Auto-detect best available provider if "auto" or if provider is duckduckgo but better options exist
    if provider == "auto" or (provider == "duckduckgo" and settings.serper_api_key):
        # Prefer Serper if API key is available (better quality)
        if settings.serper_api_key:
            try:
                logger.info(
                    "Auto-detected Serper web search (SERPER_API_KEY found)",
                    provider="serper",
                )
                return SerperWebSearchTool()
            except Exception as e:
                logger.warning(
                    "Failed to initialize Serper, falling back",
                    error=str(e),
                )
        
        # Try SearchXNG as second choice
        if settings.searchxng_host:
            try:
                logger.info(
                    "Auto-detected SearchXNG web search (SEARCHXNG_HOST found)",
                    provider="searchxng",
                )
                return SearchXNGWebSearchTool()
            except Exception as e:
                logger.warning(
                    "Failed to initialize SearchXNG, falling back",
                    error=str(e),
                )
        
        # Fall back to DuckDuckGo
        if provider == "auto":
            logger.info(
                "Auto-detected DuckDuckGo web search (no API keys found)",
                provider="duckduckgo",
            )
        return WebSearchTool()

    try:
        if provider == "serper":
            if not settings.serper_api_key:
                logger.warning(
                    "Serper provider selected but no API key found",
                    hint="Set SERPER_API_KEY environment variable",
                )
                return None
            return SerperWebSearchTool()

        elif provider == "searchxng":
            if not settings.searchxng_host:
                logger.warning(
                    "SearchXNG provider selected but no host found",
                    hint="Set SEARCHXNG_HOST environment variable",
                )
                return None
            return SearchXNGWebSearchTool()

        elif provider == "duckduckgo":
            # DuckDuckGo is always available (no API key required)
            return WebSearchTool()

        elif provider in ("brave", "tavily"):
            logger.warning(
                f"Web search provider '{provider}' not yet implemented",
                hint="Use 'serper', 'searchxng', or 'duckduckgo'",
            )
            return None

        else:
            logger.warning(f"Unknown web search provider '{provider}', falling back to DuckDuckGo")
            return WebSearchTool()

    except ConfigurationError as e:
        logger.error("Failed to create web search tool", error=str(e), provider=provider)
        return None
    except Exception as e:
        logger.error("Unexpected error creating web search tool", error=str(e), provider=provider)
        return None















