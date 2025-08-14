"""
Client for performing web research and content extraction (Upgraded for efficiency).

This module uses the Google Custom Search API to find relevant URLs and then
leverages Playwright and BeautifulSoup to scrape the text content from those
pages. It is designed to run these I/O-bound tasks concurrently for efficiency.
"""

import asyncio
from typing import List, Set, Any
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .. import config
from ..utils.logger import logger


def _sync_google_search(query: str, search_service: Any, num: int) -> List[str]:
    """Synchronous wrapper for the Google Custom Search API call."""
    try:
        enhanced_query = f"{query} -site:pinterest.com -site:amazon.com"
        logger.info(f"Executing Google search for: '{enhanced_query}'")
        result = (
            search_service.cse()
            .list(q=enhanced_query, cx=config.SEARCH_ENGINE_ID, num=num)
            .execute()
        )
        urls = [
            item.get("link", "") for item in result.get("items", []) if item.get("link")
        ]
        logger.info(f"Found {len(urls)} URLs for query: '{enhanced_query}'")
        return urls
    except HttpError as e:
        logger.error(f"HttpError {e.resp.status} for query '{query}': {e.content}")
        return []
    except Exception as e:
        logger.error(
            f"An unexpected error during Google search for '{query}': {e}",
            exc_info=True,
        )
        return []


async def _scrape_url_content(url: str) -> str:
    """
    Asynchronously scrapes and extracts the main text content from a given URL
    using an intelligent, targeted approach and robust error handling.
    """
    if not url or not url.startswith(("http://", "https://")):
        logger.warning(f"Invalid or empty URL provided: {url}")
        return ""

    logger.info(f"Starting intelligent scrape for URL: {url}")
    browser = None
    page = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            await page.route(
                "**/*",
                lambda route: (
                    route.abort()
                    if route.request.resource_type
                    in {"image", "stylesheet", "font", "media"}
                    else route.continue_()
                ),
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            html_content = await page.content()

            # CRITICAL FIX: Un-route all handlers before closing to prevent race conditions.
            await page.unroute_all(behavior="ignoreErrors")
            await browser.close()

        soup = BeautifulSoup(html_content, "html.parser")

        content_selectors = [
            "article",
            "main",
            '[role="main"]',
            "#main-content",
            "#content",
            ".article-body",
            ".post-content",
        ]
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.info(f"Found main content using selector '{selector}' for {url}")
                break

        target_soup = main_content if main_content else soup
        for element in target_soup(
            ["script", "style", "nav", "aside", "footer", "header"]
        ):
            element.decompose()

        text = " ".join(target_soup.get_text(separator=" ", strip=True).split())

        if len(text) < 200:
            logger.warning(
                f"URL {url} has insufficient content ({len(text)} chars), skipping."
            )
            return ""

        logger.info(
            f"Successfully extracted {len(text)} characters of targeted content from {url}"
        )
        return text
    except (PlaywrightError, asyncio.TimeoutError) as e:
        logger.warning(f"Scraping failed for {url}: {e}")
        return ""
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while scraping {url}: {e}", exc_info=True
        )
        return ""
    finally:
        # Ensure cleanup happens even if errors occur
        if page and not page.is_closed():
            await page.close()
        if browser and browser.is_connected():
            await browser.close()


async def gather_research_documents(queries: List[str]) -> List[str]:
    """Performs web research and returns a list of full-text documents."""
    logger.info("--- Starting Research Phase: Gathering Raw Documents ---")
    if not queries:
        logger.warning("No queries provided for research.")
        return []

    try:
        search_service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
    except Exception as e:
        logger.critical(
            f"CRITICAL: Failed to build Google Search service: {e}", exc_info=True
        )
        return []

    loop = asyncio.get_running_loop()
    search_tasks = [
        loop.run_in_executor(
            None, _sync_google_search, query, search_service, config.SEARCH_NUM_RESULTS
        )
        for query in queries
    ]
    url_lists = await asyncio.gather(*search_tasks)
    all_urls: Set[str] = {url for url_list in url_lists for url in url_list}

    if not all_urls:
        logger.warning("No URLs were found from any search query.")
        return []

    logger.info(f"Found a total of {len(all_urls)} unique URLs to scrape.")
    scraping_tasks = [_scrape_url_content(url) for url in all_urls]
    scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)

    valid_contents = [str(c) for c in scraped_contents if isinstance(c, str) and c]
    logger.info(
        f"Successfully scraped content from {len(valid_contents)} out of {len(all_urls)} URLs."
    )

    return valid_contents
