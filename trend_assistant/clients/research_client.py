"""
Client for performing web research and content extraction.
(Fixed version with proper route handling to prevent TargetClosedError)
"""

import asyncio
import random
import re
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


async def _scrape_with_fallback_strategy(page, url: str) -> str:
    """Try multiple loading strategies to ensure content is fetched."""
    strategies = [
        {"wait_until": "domcontentloaded", "timeout": 15000, "name": "fast"},
        {"wait_until": "load", "timeout": 20000, "name": "standard"},
        {"wait_until": "networkidle", "timeout": 25000, "name": "patient"},
    ]
    for i, strategy in enumerate(strategies):
        try:
            logger.debug(
                f"Trying navigation strategy #{i+1} ({strategy['name']}) for {url}"
            )
            await page.goto(
                url, wait_until=strategy["wait_until"], timeout=strategy["timeout"]
            )
            content = await page.content()
            if len(content) > 500:
                logger.debug(f"Strategy #{i+1} successful for {url}")
                return content
        except (PlaywrightTimeoutError, PlaywrightError) as e:
            logger.warning(f"Strategy #{i+1} for {url} failed: {e}")
            if i == len(strategies) - 1:
                raise
    return ""


async def _handle_cookie_banners(page) -> None:
    """Handle cookie banners with quick timeouts."""
    cookie_selectors = [
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "#onetrust-accept-btn-handler",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
    ]
    for selector in cookie_selectors:
        try:
            await page.locator(selector).click(timeout=2000)
            logger.info(f"Clicked cookie banner using selector: {selector}")
            await page.wait_for_timeout(500)
            break
        except PlaywrightError:
            continue


def _extract_text_content_enhanced(html_content: str, url: str) -> str:
    """Enhanced text extraction with better selectors and defensive programming."""
    soup = BeautifulSoup(html_content, "html.parser")
    content_selectors = [
        ".blog-post-content",
        ".trend-analysis",
        ".fashion-content",
        ".post-content",
        ".article-content",
        ".blog-content",
        "article",
        "main",
        '[role="main"]',
        ".main-content",
        "#main-content",
        "#content",
        ".content",
        ".article-body",
        ".post-body",
        ".entry-content",
        ".blog-post",
        ".container",
        ".wrapper",
        "#wrapper",
    ]
    main_content = None
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        # DEFENSIVE CHECK: Ensure main_content is not None before using it
        if main_content and len(main_content.get_text(strip=True)) > 300:
            logger.debug(f"Found content with selector: {selector}")
            break

    target_soup = main_content if main_content else soup

    junk_selectors = [
        ".comments",
        "#comments",
        ".comment-section",
        ".social-share",
        ".social-sharing",
        ".share-buttons",
        ".advertisement",
        ".ads",
        ".ad-container",
        ".newsletter-signup",
        ".newsletter",
        ".email-signup",
        ".promo",
        ".promotion",
        ".banner-ad",
        ".modal",
        ".popup",
        ".overlay",
        ".cookie-banner",
        ".cookie-notice",
        ".gdpr-notice",
        ".sidebar",
        "#sidebar",
        ".widget",
        ".widgets",
        ".related-posts",
        ".related-articles",
        ".recommended",
        ".more-stories",
        ".trending",
        ".author-bio",
        ".author-info",
        ".tags",
        ".categories",
        ".post-meta",
        ".contact-form",
        ".search-form",
        "form.search",
    ]
    for junk_selector in junk_selectors:
        for element in target_soup.select(junk_selector):
            element.decompose()

    for element in target_soup(
        ["script", "style", "noscript", "nav", "aside", "footer", "header"]
    ):
        element.decompose()

    # DEFINITIVE FIX: Use BeautifulSoup's robust text extraction, then clean.
    text = target_soup.get_text(separator=" ", strip=True)
    cleaned_text = re.sub(r"\s+", " ", text).strip()
    cleaned_text = re.sub(
        r"(Share:|Follow us:|Subscribe|Newsletter)",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    if len(cleaned_text) < 200:
        logger.warning(
            f"URL {url} has insufficient content ({len(cleaned_text)} chars)"
        )
        return ""

    return cleaned_text[:50000]


async def _defensive_route_handler(route, request):
    """Defensive route handler that prevents TargetClosedError."""
    try:
        # Block resource types that we don't need
        if request.resource_type in {"image", "font", "media", "websocket"}:
            await route.abort()
        else:
            await route.continue_()
    except Exception as e:
        # Handle cases where page/context/browser has been closed
        error_message = str(e)
        if any(
            keyword in error_message
            for keyword in [
                "Target page",
                "Target closed",
                "TargetClosedError",
                "context disposed",
                "browser closed",
            ]
        ):
            # This is a harmless race condition - just ignore it
            logger.debug(f"Route handler called after page closed: {e}")
            return
        # Re-raise other unexpected errors
        logger.error(f"Unexpected route handler error: {e}")
        raise


async def _scrape_single_url_enhanced(url: str) -> str:
    """Internal scraping function with proper resource management and route cleanup."""
    browser = None
    context = None
    page = None
    html_content = ""

    try:
        async with Stealth().use_async(async_playwright()) as p:  # type: ignore
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            page.set_default_timeout(20000)

            # Set up route with defensive handler
            await page.route("**/*", _defensive_route_handler)

            html_content = await _scrape_with_fallback_strategy(page, url)
            if html_content:
                await _handle_cookie_banners(page)
                html_content = await page.content()

    except Exception as e:
        logger.warning(f"Enhanced scraping error for {url}: {e}")
    finally:
        # CRITICAL: Clean up routes before closing to prevent TargetClosedError
        try:
            if page:
                # Unregister all routes with error ignoring behavior
                await page.unroute_all(behavior="ignoreErrors")
        except Exception as cleanup_error:
            logger.debug(f"Route cleanup error (harmless): {cleanup_error}")

        try:
            if context:
                await context.close()
        except Exception as context_error:
            logger.debug(f"Context close error (harmless): {context_error}")

        try:
            if browser:
                await browser.close()
        except Exception as browser_error:
            logger.debug(f"Browser close error (harmless): {browser_error}")

    if not html_content:
        return ""
    return _extract_text_content_enhanced(html_content, url)


async def _scrape_url_content(url: str) -> str:
    """Wraps the internal scraping function with a total operation timeout."""
    try:
        return await asyncio.wait_for(_scrape_single_url_enhanced(url), timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning(f"Total scraping timeout (30s) exceeded for {url}")
        return ""


async def gather_research_documents(queries: List[str]) -> List[str]:
    """Enhanced research gathering with controlled concurrency."""
    logger.info("--- Starting Enhanced Research Phase: Gathering Raw Documents ---")
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
    ignored_domains = [
        "pinterest.com",
        "amazon.com",
        "instagram.com",
        "facebook.com",
        "twitter.com",
        "youtube.com",
    ]
    filtered_urls = [
        url
        for url in all_urls
        if not any(url.lower().endswith(ext) for ext in ignored_extensions)
        and not any(domain in url.lower() for domain in ignored_domains)
    ]

    if len(all_urls) > len(filtered_urls):
        logger.info(
            f"Filtered out {len(all_urls) - len(filtered_urls)} unsuitable URLs"
        )
    if not filtered_urls:
        return []

    logger.info(f"Found {len(filtered_urls)} valid URLs to scrape")

    semaphore = asyncio.Semaphore(4)

    async def scrape_with_semaphore(url):
        async with semaphore:
            return await _scrape_url_content(url)

    scraping_tasks = [scrape_with_semaphore(url) for url in filtered_urls]
    scraped_contents = await asyncio.gather(*scraping_tasks, return_exceptions=True)

    valid_contents = [c for c in scraped_contents if isinstance(c, str) and c]
    logger.info(
        f"Successfully scraped {len(valid_contents)} out of {len(filtered_urls)} URLs"
    )
    return valid_contents
