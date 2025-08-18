"""
Client for performing web research and content extraction.
(Fixed version with language filtering and corrected type handling)
"""

import asyncio
import random
import re
from typing import List, Set, Any, Dict, Union
from bs4 import BeautifulSoup
from playwright.async_api import (
    async_playwright,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright_stealth import Stealth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langdetect import detect, LangDetectException
from .. import config
from ..utils.logger import logger
from ..utils import output_utils

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

ScrapeResult = Dict[str, Any]


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
        return urls
    except Exception as e:
        logger.error(
            f"An unexpected error during Google search for '{query}': {e}",
            exc_info=True,
        )
        return []


async def _scrape_single_url_enhanced(url: str) -> ScrapeResult:
    """Internal scraping function with proper resource management."""
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # Simplified cookie handling
            cookie_selectors = [
                "button:has-text('Accept')",
                "button:has-text('Agree')",
                ".cookie-accept",
            ]
            for selector in cookie_selectors:
                try:
                    await page.locator(selector).first.click(timeout=1500)
                    logger.info(f"Clicked cookie banner for {url}")
                    await page.wait_for_timeout(500)
                    break
                except PlaywrightError:
                    continue

            html_content = await page.content()

            soup = BeautifulSoup(html_content, "html.parser")
            for element in soup(
                ["script", "style", "nav", "aside", "footer", "header", "form"]
            ):
                element.decompose()

            text = soup.get_text(separator=" ", strip=True)
            cleaned_text = re.sub(r"\s+", " ", text).strip()

            if len(cleaned_text) < 200:
                return {
                    "status": "partial",
                    "url": url,
                    "content": cleaned_text,
                    "reason": f"Insufficient content length: {len(cleaned_text)}",
                }

            return {"status": "success", "url": url, "content": cleaned_text}

    except Exception as e:
        return {"status": "failed", "url": url, "reason": str(e)}
    finally:
        if browser:
            await browser.close()


async def gather_research_documents(queries: List[str]) -> List[str]:
    """Enhanced research gathering with language filtering and robust error handling."""
    logger.info("--- Starting Enhanced Research Phase ---")
    search_service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
    loop = asyncio.get_running_loop()
    search_tasks = [
        loop.run_in_executor(
            None, _sync_google_search, q, search_service, config.SEARCH_NUM_RESULTS
        )
        for q in queries
    ]
    url_lists = await asyncio.gather(*search_tasks)
    all_urls = {url for url_list in url_lists for url in url_list}

    ignored_domains = [
        "pinterest.com",
        "amazon.com",
        "instagram.com",
        "facebook.com",
        "twitter.com",
        "youtube.com",
        "tiktok.com",
        "linkedin.com",
    ]
    filtered_urls = [
        url
        for url in all_urls
        if not any(domain in url.lower() for domain in ignored_domains)
    ]

    logger.info(f"Found {len(filtered_urls)} valid URLs to scrape.")

    # Use a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(4)

    async def scrape_with_semaphore(url: str):
        async with semaphore:
            return await _scrape_single_url_enhanced(url)

    scraping_tasks = [scrape_with_semaphore(url) for url in filtered_urls]

    # This list can contain either ScrapeResult or an Exception
    results_from_gather: List[Union[ScrapeResult, BaseException]] = (
        await asyncio.gather(*scraping_tasks, return_exceptions=True)
    )

    # This list will ONLY contain ScrapeResult dictionaries, satisfying the type checker
    processed_results: List[ScrapeResult] = []
    for i, res in enumerate(results_from_gather):
        if isinstance(res, BaseException):
            # Convert the exception to a valid ScrapeResult dictionary
            processed_results.append(
                {
                    "status": "failed",
                    "url": filtered_urls[i],
                    "reason": f"Gather task failed: {res}",
                }
            )
        else:
            # The result is already a valid ScrapeResult dictionary
            processed_results.append(res)

    output_utils.save_scraping_report(processed_results)

    logger.info("Filtering scraped content for English language documents...")
    valid_contents = []
    for res in processed_results:
        # Check for content before trying to detect language
        content = res.get("content")
        if res.get("status") in ["success", "partial"] and content:
            try:
                # Ensure content is a string and not empty
                if isinstance(content, str) and len(content.strip()) > 10:
                    if detect(content) == "en":
                        valid_contents.append(content)
                    else:
                        logger.warning(
                            f"Skipping non-English content from URL: {res['url']}"
                        )
                else:
                    logger.warning(
                        f"Skipping empty or invalid content from URL: {res['url']}"
                    )
            except LangDetectException:
                logger.warning(
                    f"Could not determine language for URL {res['url']}. Skipping."
                )

    logger.info(f"Retained {len(valid_contents)} English documents for summarization.")
    return valid_contents
