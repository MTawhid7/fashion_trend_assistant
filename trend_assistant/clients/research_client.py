"""
Client for performing web research and content extraction.
(Final version with enhanced speed, resilience, and cookie handling)
"""

import asyncio
import random
from typing import List, Set, Any
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Error as PlaywrightError
from playwright_stealth import Stealth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .. import config
from ..utils.logger import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


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
    """Asynchronously scrapes and extracts content with advanced techniques."""
    if not url or not url.startswith(("http://", "https://")):
        return ""

    logger.info(f"Starting advanced scrape for URL: {url}")
    browser = None
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(
                {"User-Agent": random.choice(USER_AGENTS)}
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

            # --- UPGRADED WAIT STRATEGY ---
            # Go to the page and wait for the initial document to load. This is fast.
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)

            # --- NEW: Handle Cookie Banners ---
            # A list of common selectors for "accept" buttons on cookie banners.
            cookie_selectors = [
                "button:has-text('Accept')",
                "button:has-text('Agree')",
                "button:has-text('I understand')",
                "button:has-text('Allow all')",
                "#onetrust-accept-btn-handler",
            ]
            for selector in cookie_selectors:
                try:
                    # Look for the button and click it, with a short timeout.
                    await page.locator(selector).click(timeout=5000)
                    logger.info(f"Successfully clicked cookie banner on {url}")
                    # Wait for a moment for the banner to disappear.
                    await page.wait_for_timeout(1000)
                    break  # Stop looking once we've clicked one.
                except PlaywrightError:
                    # This is not an error, it just means the button wasn't found.
                    pass

            # --- UPGRADED: More Patient Smart Wait ---
            # Now, wait patiently for the main content to appear.
            content_selectors = [
                "article",
                "main",
                '[role="main"]',
                "#main-content",
                "#content",
                ".article-body",
                ".post-content",
            ]
            combined_selector = ", ".join(content_selectors)
            try:
                await page.wait_for_selector(
                    combined_selector, state="visible", timeout=25000
                )
                logger.info(
                    f"Smart wait successful: Found a content selector for {url}"
                )
            except PlaywrightError:
                logger.warning(
                    f"Smart wait timed out for {url}. Proceeding with available HTML."
                )

            html_content = await page.content()
            await page.unroute_all(behavior="ignoreErrors")
            await page.close()
            await browser.close()

        soup = BeautifulSoup(html_content, "html.parser")

        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.info(
                    f"Surgical extraction successful with selector '{selector}' for {url}"
                )
                break

        target_soup = main_content if main_content else soup
        junk_selectors = [
            ".comments",
            "#comments",
            ".related-posts",
            ".sidebar",
            "#sidebar",
            ".social-share",
            ".newsletter-signup",
            "author-bio",
        ]
        for junk_selector in junk_selectors:
            for element in target_soup.select(junk_selector):
                element.decompose()
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
        if browser and browser.is_connected():
            await browser.close()


async def gather_research_documents(queries: List[str]) -> List[str]:
    """Performs web research and returns a list of full-text documents."""
    logger.info("--- Starting Research Phase: Gathering Raw Documents ---")
    if not queries:
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
        return []

    ignored_extensions = [
        ".pdf",
        ".txt",
        ".zip",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".docx",
        ".xlsx",
    ]
    filtered_urls = [
        url
        for url in all_urls
        if not any(url.lower().endswith(ext) for ext in ignored_extensions)
    ]

    if len(all_urls) > len(filtered_urls):
        logger.info(
            f"Filtered out {len(all_urls) - len(filtered_urls)} direct file links."
        )

    if not filtered_urls:
        return []

    logger.info(f"Found a total of {len(filtered_urls)} valid URLs to scrape.")
    scraping_tasks = [_scrape_url_content(url) for url in filtered_urls]
    scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)
    valid_contents = [str(c) for c in scraped_contents if isinstance(c, str) and c]
    logger.info(
        f"Successfully scraped content from {len(valid_contents)} out of {len(filtered_urls)} URLs."
    )

    return valid_contents
