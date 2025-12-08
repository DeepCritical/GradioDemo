"""Vendored web search components from folder/tools/web_search.py."""

from src.tools.vendored.crawl_website import crawl_website
from src.tools.vendored.searchxng_client import SearchXNGClient
from src.tools.vendored.serper_client import SerperClient
from src.tools.vendored.web_search_core import (
    CONTENT_LENGTH_LIMIT,
    ScrapeResult,
    WebpageSnippet,
    fetch_and_process_url,
    html_to_text,
    is_valid_url,
    scrape_urls,
)

__all__ = [
    "CONTENT_LENGTH_LIMIT",
    "ScrapeResult",
    "SearchXNGClient",
    "SerperClient",
    "WebpageSnippet",
    "crawl_website",
    "fetch_and_process_url",
    "html_to_text",
    "is_valid_url",
    "scrape_urls",
]
