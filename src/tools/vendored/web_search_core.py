"""Core web search utilities vendored from folder/tools/web_search.py.

This module contains shared utilities for web scraping, URL processing,
and HTML text extraction used by web search tools.
"""

import asyncio
import ssl

import aiohttp
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Content length limit to avoid exceeding token limits
CONTENT_LENGTH_LIMIT = 10000

# Create a shared SSL context for web requests
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")  # Allow older cipher suites


class ScrapeResult(BaseModel):
    """Result of scraping a single webpage."""

    url: str = Field(description="The URL of the webpage")
    text: str = Field(description="The full text content of the webpage")
    title: str = Field(description="The title of the webpage")
    description: str = Field(description="A short description of the webpage")


class WebpageSnippet(BaseModel):
    """Snippet information for a webpage (before scraping)."""

    url: str = Field(description="The URL of the webpage")
    title: str = Field(description="The title of the webpage")
    description: str | None = Field(default=None, description="A short description of the webpage")


async def scrape_urls(items: list[WebpageSnippet]) -> list[ScrapeResult]:
    """Fetch text content from provided URLs.

    Args:
        items: List of WebpageSnippet items to extract content from

    Returns:
        List of ScrapeResult objects with scraped content
    """
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Create list of tasks for concurrent execution
        tasks = []
        for item in items:
            if item.url:  # Skip empty URLs
                tasks.append(fetch_and_process_url(session, item))

        # Execute all tasks concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors and return successful results
        successful_results: list[ScrapeResult] = []
        for result in results:
            if isinstance(result, ScrapeResult):
                successful_results.append(result)
            elif isinstance(result, Exception):
                logger.warning("Failed to scrape URL", error=str(result))

        return successful_results


async def fetch_and_process_url(
    session: aiohttp.ClientSession, item: WebpageSnippet
) -> ScrapeResult:
    """Helper function to fetch and process a single URL.

    Args:
        session: aiohttp ClientSession
        item: WebpageSnippet with URL to fetch

    Returns:
        ScrapeResult with fetched content
    """
    if not is_valid_url(item.url):
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description or "",
            text="Error fetching content: URL contains restricted file extension",
        )

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with session.get(item.url, timeout=timeout) as response:
            if response.status == 200:
                content = await response.text()
                # Run html_to_text in a thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                text_content = await loop.run_in_executor(None, html_to_text, content)
                text_content = text_content[
                    :CONTENT_LENGTH_LIMIT
                ]  # Trim content to avoid exceeding token limit
                return ScrapeResult(
                    url=item.url,
                    title=item.title,
                    description=item.description or "",
                    text=text_content,
                )
            else:
                # Return a ScrapeResult with an error message
                return ScrapeResult(
                    url=item.url,
                    title=item.title,
                    description=item.description or "",
                    text=f"Error fetching content: HTTP {response.status}",
                )
    except Exception as e:
        logger.warning("Error fetching URL", url=item.url, error=str(e))
        # Return a ScrapeResult with an error message
        return ScrapeResult(
            url=item.url,
            title=item.title,
            description=item.description or "",
            text=f"Error fetching content: {e!s}",
        )


def html_to_text(html_content: str) -> str:
    """Strip out unnecessary elements from HTML to prepare for text extraction.

    Args:
        html_content: Raw HTML content

    Returns:
        Extracted text from relevant HTML tags
    """
    # Parse the HTML using lxml for speed
    soup = BeautifulSoup(html_content, "lxml")

    # Extract text from relevant tags
    tags_to_extract = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")

    # Use a generator expression for efficiency
    extracted_text = "\n".join(
        element.get_text(strip=True)
        for element in soup.find_all(tags_to_extract)
        if element.get_text(strip=True)
    )

    return extracted_text


def is_valid_url(url: str) -> bool:
    """Check that a URL does not contain restricted file extensions.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid, False if it contains restricted extensions
    """
    restricted_extensions = [
        ".pdf",
        ".doc",
        ".xls",
        ".ppt",
        ".zip",
        ".rar",
        ".7z",
        ".txt",
        ".js",
        ".xml",
        ".css",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".webp",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".wma",
        ".wav",
        ".m4a",
        ".m4v",
        ".m4b",
        ".m4p",
        ".m4u",
    ]

    if any(ext in url for ext in restricted_extensions):
        return False
    return True









