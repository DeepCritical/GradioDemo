"""Factory for creating web search tools based on configuration."""

import structlog

from src.tools.base import SearchTool
from src.tools.searchxng_web_search import SearchXNGWebSearchTool
from src.tools.serper_web_search import SerperWebSearchTool
from src.tools.web_search import WebSearchTool
from src.utils.config import settings
from src.utils.exceptions import ConfigurationError

logger = structlog.get_logger()


def create_web_search_tool() -> SearchTool | None:
    """Create a web search tool based on configuration.

    Returns:
        SearchTool instance, or None if not available/configured

    The tool is selected based on settings.web_search_provider:
    - "serper": SerperWebSearchTool (requires SERPER_API_KEY)
    - "searchxng": SearchXNGWebSearchTool (requires SEARCHXNG_HOST)
    - "duckduckgo": WebSearchTool (always available, no API key)
    - "brave" or "tavily": Not yet implemented, returns None
    """
    provider = settings.web_search_provider

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


