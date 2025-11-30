"""Web search tool adapter for Pydantic AI agents.

Uses the new web search factory to provide web search functionality.
"""

import structlog

from src.tools.web_search_factory import create_web_search_tool

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
        # Get web search tool from factory
        tool = create_web_search_tool()

        if tool is None:
            logger.warning("Web search tool not available", hint="Check configuration")
            return "Web search tool not available. Please configure a web search provider."

        # Call the tool - it returns list[Evidence]
        evidence = await tool.search(query, max_results=5)

        if not evidence:
            return f"No web search results found for: {query}"

        # Format results for agent consumption
        formatted = [f"Found {len(evidence)} web search results:\n"]
        for i, ev in enumerate(evidence, 1):
            citation = ev.citation
            formatted.append(f"{i}. **{citation.title}**")
            if citation.url:
                formatted.append(f"   URL: {citation.url}")
            if ev.content:
                formatted.append(f"   Content: {ev.content[:300]}...")
            formatted.append("")

        return "\n".join(formatted)

    except Exception as e:
        logger.error("Web search failed", error=str(e), query=query)
        return f"Error performing web search: {e!s}"







