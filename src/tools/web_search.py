"""Web search tool using Tavily API."""

import asyncio

import structlog
from tavily import TavilyClient

from src.utils.config import settings
from src.utils.models import Citation, Evidence

logger = structlog.get_logger()


class WebSearchTool:
    """Tool for searching the web using Tavily."""

    def __init__(self) -> None:
        self.api_key = settings.tavily_api_key
        if not self.api_key:
            logger.warning("No Tavily API key found - web search will fail")

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "web"

    async def search(self, query: str, max_results: int = 10) -> list[Evidence]:
        """Execute a web search."""
        try:
            # DuckDuckGo implementation (commented out)
            # loop = asyncio.get_running_loop()
            # def _do_search() -> list[dict[str, str]]:
            #     return list(self._ddgs.text(query, region='us-en', safesearch="moderate", max_results=max_results))
            # raw_results = await loop.run_in_executor(None, _do_search)
            
            client = TavilyClient(api_key=self.api_key)
            
            loop = asyncio.get_running_loop()
            
            def _do_search() -> dict:
                return client.search(query=query, max_results=max_results)
            
            response = await loop.run_in_executor(None, _do_search)

            evidence = []
            for r in response.get("results", []):
                ev = Evidence(
                    content=r.get("content", ""),
                    citation=Citation(
                        title=r.get("title", "No Title"),
                        url=r.get("url", ""),
                        source="web",
                        date="Unknown",
                        authors=[],
                    ),
                    relevance=r.get("score", 0.0),
                )
                evidence.append(ev)

            return evidence

        except Exception as e:
            logger.error("Web search failed", error=str(e))
            return []
