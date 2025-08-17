"""
Client for performing web research and content extraction.
(Fixed version that prevents hanging after successful extractions)
"""

import asyncio
import random
from typing import List, Set, Any
from bs4 import BeautifulSoup
from playwright.async_api import (
    async_playwright,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)
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


async def _scrape_with_fast_strategy(page, url: str) -> str:
    """Fast, no-nonsense navigation strategy to prevent hanging."""
    strategies = [
        {"wait_until": "commit", "timeout": 3000, "name": "commit"},
        {"wait_until": "domcontentloaded", "timeout": 5000, "name": "dom"},
        {"wait_until": None, "timeout": 2000, "name": "minimal"},
    ]

    for i, strategy in enumerate(strategies):
        try:
            logger.debug(f"Trying strategy {i+1} ({strategy['name']}) for {url}")

            if strategy["wait_until"]:
                await page.goto(
                    url, wait_until=strategy["wait_until"], timeout=strategy["timeout"]
                )
            else:
                await page.goto(url, timeout=strategy["timeout"])

            # Get content immediately, no additional waiting
            content = await page.content()
            if len(content) > 300:  # Basic sanity check
                return content

        except (PlaywrightTimeoutError, PlaywrightError):
            if i < len(strategies) - 1:
                continue
            else:
                # Last resort - try to get any content
                try:
                    return await page.content()
                except Exception:
                    return ""

    return ""


async def _handle_cookie_banners_fast(page) -> None:
    """Quick cookie banner handling with very short timeouts."""
    cookie_selectors = [
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "#onetrust-accept-btn-handler",
    ]

    for selector in cookie_selectors:
        try:
            await page.locator(selector).click(timeout=1000)  # Very short timeout
            await page.wait_for_timeout(200)  # Brief pause
            break
        except PlaywrightError:
            continue


async def _scrape_url_content(url: str) -> str:
    """
    Fixed scraping function that prevents hanging after successful extractions.
    """
    if not url or not url.startswith(("http://", "https://")):
        return ""

    logger.info(f"Starting scrape for URL: {url}")

    # Wrap entire operation in timeout to prevent infinite hanging
    try:
        result = await asyncio.wait_for(_scrape_single_url(url), timeout=15.0)
        if result:
            logger.info(f"Successfully extracted {len(result)} characters from {url}")
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Total timeout (15s) exceeded for {url}")
        return ""
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        return ""


async def _scrape_single_url(url: str) -> str:
    """Internal scraping with deterministic cleanup."""
    playwright_ctx = None
    browser = None
    page = None
    html_content = ""

    try:
        # Use context manager for Playwright but handle cleanup manually
        playwright_ctx = await async_playwright().start()

        browser = await playwright_ctx.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-timer-throttling",
            ],
        )

        page = await browser.new_page()

        # Set short timeouts
        page.set_default_timeout(6000)
        page.set_default_navigation_timeout(6000)

        await page.set_extra_http_headers({"User-Agent": random.choice(USER_AGENTS)})

        # Block resource-heavy content
        await page.route(
            "**/*",
            lambda route: (
                route.abort()
                if route.request.resource_type
                in {"image", "stylesheet", "font", "media", "websocket"}
                else route.continue_()
            ),
        )

        # Use fast navigation strategy
        html_content = await _scrape_with_fast_strategy(page, url)

        # Quick cookie handling if we got content
        if html_content:
            await _handle_cookie_banners_fast(page)
            # Don't re-fetch content after cookie handling to avoid hanging

    except Exception as e:
        logger.warning(f"Scraping error for {url}: {e}")
        html_content = ""

    finally:
        # CRITICAL: Deterministic cleanup with individual timeouts
        cleanup_errors = []

        # Close page first
        if page:
            try:
                await asyncio.wait_for(page.close(), timeout=1.0)
            except Exception as e:
                cleanup_errors.append(f"page: {e}")

        # Close browser
        if browser:
            try:
                await asyncio.wait_for(browser.close(), timeout=1.0)
            except Exception as e:
                cleanup_errors.append(f"browser: {e}")

        # Stop playwright
        if playwright_ctx:
            try:
                await asyncio.wait_for(playwright_ctx.stop(), timeout=1.0)
            except Exception as e:
                cleanup_errors.append(f"playwright: {e}")

        if cleanup_errors:
            logger.debug(f"Cleanup issues for {url}: {cleanup_errors}")

    # Process content if we got any
    if not html_content:
        return ""

    return _extract_text_content(html_content, url)


def _extract_text_content(html_content: str, url: str) -> str:
    """Extract text content from HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Try to find main content
    content_selectors = [
        "article",
        "main",
        '[role="main"]',
        "#main-content",
        "#content",
        ".article-body",
        ".post-content",
        ".entry-content",
        ".content",
    ]

    main_content = None
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    target_soup = main_content if main_content else soup

    # Remove unwanted elements
    junk_selectors = [
        ".comments",
        "#comments",
        ".related-posts",
        ".sidebar",
        "#sidebar",
        ".social-share",
        ".newsletter-signup",
        ".author-bio",
        ".advertisement",
        ".ads",
        ".cookie-banner",
        ".popup",
        ".modal",
    ]

    for junk_selector in junk_selectors:
        for element in target_soup.select(junk_selector):
            element.decompose()

    for element in target_soup(
        ["script", "style", "nav", "aside", "footer", "header", "noscript"]
    ):
        element.decompose()

    text = " ".join(target_soup.get_text(separator=" ", strip=True).split())

    if len(text) < 200:
        logger.warning(f"URL {url} has insufficient content ({len(text)} chars)")
        return ""

    return text


async def gather_research_documents(queries: List[str]) -> List[str]:
    """Improved research gathering with controlled concurrency and better error handling."""
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

    # Get URLs from search
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

    # Filter URLs
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
            f"Filtered out {len(all_urls) - len(filtered_urls)} direct file links"
        )

    if not filtered_urls:
        return []

    logger.info(f"Found {len(filtered_urls)} valid URLs to scrape")

    # Use controlled concurrency with semaphore
    semaphore = asyncio.Semaphore(4)  # Reduced concurrency to prevent overwhelming

    async def scrape_with_semaphore(url):
        async with semaphore:
            return await _scrape_url_content(url)

    # Execute scraping tasks
    scraping_tasks = [scrape_with_semaphore(url) for url in filtered_urls]
    scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)

    # Filter valid results
    valid_contents = []
    for i, content in enumerate(scraped_contents):
        if isinstance(content, str) and content:
            valid_contents.append(content)
        elif isinstance(content, Exception):
            logger.warning(f"Scraping exception for URL {i}: {content}")

    logger.info(
        f"Successfully scraped {len(valid_contents)} out of {len(filtered_urls)} URLs"
    )
    return valid_contents
