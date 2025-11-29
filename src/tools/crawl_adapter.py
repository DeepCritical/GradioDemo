"""Website crawl tool adapter for Pydantic AI agents.

Adapts the folder/tools/crawl_website.py implementation to work with Pydantic AI.
"""

import structlog

logger = structlog.get_logger()


async def crawl_website(starting_url: str) -> str:
    """
    Crawl a website starting from the given URL and return formatted results.

    Use this tool to crawl a website for information relevant to the query.
    Provide a starting URL as input.

    Args:
        starting_url: The starting URL to crawl (e.g., "https://example.com")

    Returns:
        Formatted string with crawled content including titles, descriptions, and URLs
    """
    try:
        # Lazy import to avoid requiring folder/ dependencies at import time
        from folder.tools.crawl_website import crawl_website as crawl_tool

        # Call the tool function
        # The tool returns List[ScrapeResult] or str
        results = await crawl_tool(starting_url)

        if isinstance(results, str):
            # Error message returned
            logger.warning("Crawl returned error", error=results)
            return results

        if not results:
            return f"No content found when crawling: {starting_url}"

        # Format results for agent consumption
        formatted = [f"Found {len(results)} pages from {starting_url}:\n"]
        for i, result in enumerate(results[:10], 1):  # Limit to 10 pages
            formatted.append(f"{i}. **{result.title or 'Untitled'}**")
            if result.description:
                formatted.append(f"   {result.description[:200]}...")
            formatted.append(f"   URL: {result.url}")
            if result.text:
                formatted.append(f"   Content: {result.text[:500]}...")
            formatted.append("")

        return "\n".join(formatted)

    except ImportError as e:
        logger.error("Crawl tool not available", error=str(e))
        return f"Crawl tool not available: {e!s}"
    except Exception as e:
        logger.error("Crawl failed", error=str(e), url=starting_url)
        return f"Error crawling website: {e!s}"
