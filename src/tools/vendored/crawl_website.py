"""Website crawl tool vendored from folder/tools/crawl_website.py.

This module provides website crawling functionality that starts from a given URL
and crawls linked pages in a breadth-first manner, prioritizing navigation links.
"""

from urllib.parse import urljoin, urlparse

import aiohttp
import structlog
from bs4 import BeautifulSoup

from src.tools.vendored.web_search_core import (
    ScrapeResult,
    WebpageSnippet,
    scrape_urls,
    ssl_context,
)

logger = structlog.get_logger()


async def crawl_website(starting_url: str) -> list[ScrapeResult] | str:
    """Crawl the pages of a website starting with the starting_url and then descending into the pages linked from there.

    Prioritizes links found in headers/navigation, then body links, then subsequent pages.

    Args:
        starting_url: Starting URL to scrape

    Returns:
        List of ScrapeResult objects which have the following fields:
            - url: The URL of the web page
            - title: The title of the web page
            - description: The description of the web page
            - text: The text content of the web page
    """
    if not starting_url:
        return "Empty URL provided"

    # Ensure URL has a protocol
    if not starting_url.startswith(("http://", "https://")):
        starting_url = "http://" + starting_url

    max_pages = 10
    base_domain = urlparse(starting_url).netloc

    async def extract_links(html: str, current_url: str) -> tuple[list[str], list[str]]:
        """Extract prioritized links from HTML content"""
        soup = BeautifulSoup(html, "html.parser")
        nav_links = set()
        body_links = set()

        # Find navigation/header links
        for nav_element in soup.find_all(["nav", "header"]):
            for a in nav_element.find_all("a", href=True):
                link = urljoin(current_url, a["href"])
                if urlparse(link).netloc == base_domain:
                    nav_links.add(link)

        # Find remaining body links
        for a in soup.find_all("a", href=True):
            link = urljoin(current_url, a["href"])
            if urlparse(link).netloc == base_domain and link not in nav_links:
                body_links.add(link)

        return list(nav_links), list(body_links)

    async def fetch_page(url: str) -> str:
        """Fetch HTML content from a URL"""
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        return await response.text()
                    return ""
            except Exception as e:
                logger.warning("Error fetching URL", url=url, error=str(e))
                return ""

    # Initialize with starting URL
    queue: list[str] = [starting_url]
    next_level_queue: list[str] = []
    all_pages_to_scrape: set[str] = set([starting_url])

    # Breadth-first crawl
    while queue and len(all_pages_to_scrape) < max_pages:
        current_url = queue.pop(0)

        # Fetch and process the page
        html_content = await fetch_page(current_url)
        if html_content:
            nav_links, body_links = await extract_links(html_content, current_url)

            # Add unvisited nav links to current queue (higher priority)
            remaining_slots = max_pages - len(all_pages_to_scrape)
            for link in nav_links:
                link = link.rstrip("/")
                if link not in all_pages_to_scrape and remaining_slots > 0:
                    queue.append(link)
                    all_pages_to_scrape.add(link)
                    remaining_slots -= 1

            # Add unvisited body links to next level queue (lower priority)
            for link in body_links:
                link = link.rstrip("/")
                if link not in all_pages_to_scrape and remaining_slots > 0:
                    next_level_queue.append(link)
                    all_pages_to_scrape.add(link)
                    remaining_slots -= 1

        # If current queue is empty, add next level links
        if not queue:
            queue = next_level_queue
            next_level_queue = []

    # Convert set to list for final processing
    pages_to_scrape = list(all_pages_to_scrape)[:max_pages]
    pages_to_scrape_snippets: list[WebpageSnippet] = [
        WebpageSnippet(url=page, title="", description="") for page in pages_to_scrape
    ]

    # Use scrape_urls to get the content for all discovered pages
    result = await scrape_urls(pages_to_scrape_snippets)
    return result



