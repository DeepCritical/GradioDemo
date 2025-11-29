"""Web search tool adapter for Pydantic AI agents.

Adapts the folder/tools/web_search.py implementation to work with Pydantic AI.
"""

import structlog

logger = structlog.get_logger()


async def web_search(query: str) -> str:
    """
    Perform a web search for a given query and return formatted results.

    Use this tool to search the web for information relevant to the query.
    Provide a query with 3-6 words as input.

    Args:
        query: The search query (3-6 words recommended)

    Returns:
        Formatted string with search results including titles, descriptions, and URLs
    """
    try:
        # Lazy import to avoid requiring folder/ dependencies at import time
        # This will use the existing web_search tool from folder/tools
        from folder.llm_config import create_default_config
        from folder.tools.web_search import create_web_search_tool

        config = create_default_config()
        web_search_tool = create_web_search_tool(config)

        # Call the tool function
        # The tool returns List[ScrapeResult] or str
        results = await web_search_tool(query)

        if isinstance(results, str):
            # Error message returned
            logger.warning("Web search returned error", error=results)
            return results

        if not results:
            return f"No web search results found for: {query}"

        # Format results for agent consumption
        formatted = [f"Found {len(results)} web search results:\n"]
        for i, result in enumerate(results[:5], 1):  # Limit to 5 results
            formatted.append(f"{i}. **{result.title}**")
            if result.description:
                formatted.append(f"   {result.description[:200]}...")
            formatted.append(f"   URL: {result.url}")
            if result.text:
                formatted.append(f"   Content: {result.text[:300]}...")
            formatted.append("")

        return "\n".join(formatted)

    except ImportError as e:
        logger.error("Web search tool not available", error=str(e))
        return f"Web search tool not available: {e!s}"
    except Exception as e:
        logger.error("Web search failed", error=str(e), query=query)
        return f"Error performing web search: {e!s}"
