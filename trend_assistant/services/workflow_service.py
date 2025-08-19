"""
Core Workflow Service for the Fashion Trend Assistant.
(Definitive version with modular helpers, self-correction, and robust input handling)
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Coroutine, Optional, Sequence
from pydantic import ValidationError

from . import cache_service
from .. import config
from ..clients import llm_client, research_client
from ..models.trend_models import FashionTrendReport
from ..prompts import prompt_library
from ..utils.logger import logger
from ..utils import output_utils  # We no longer need brief_utils here
from ..utils.location_helper import get_location_from_ip


# --- Helper Functions --------------------------------------------------------
def _generate_search_queries(brief: dict) -> List[str]:
    """
    Creates a definitive, multi-tiered list of search queries from the brief.
    """
    logger.info(
        "Generating a definitive, consolidated set of professional search queries..."
    )

    season, year, theme_hint = brief["season"], brief["year"], brief["theme_hint"]
    target_audience, region = brief["target_audience"], brief["region"]

    audience_query = f" for {target_audience}" if target_audience else ""
    region_search_query = f" in {region}" if region else ""

    tier1_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR trend report OR collection review OR runway analysis) "
        f"(Vogue OR WWD OR Business of Fashion OR Elle){region_search_query}"
    )
    tier2_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR key trends OR forecast OR color OR fabric) "
        f"(WGSN OR Trendstop OR Pantone OR Première Vision)"
    )
    tier3_query1 = f"({theme_hint} OR key pieces OR must-have items) {season} {year}{region_search_query}"
    tier3_query2 = (
        f"latest street style {theme_hint}{region_search_query}{audience_query}"
    )
    tier4_query1 = (
        f"'{theme_hint}' aesthetic in contemporary art and fashion{region_search_query}"
    )
    tier4_query2 = f"'{theme_hint}' film and cinema costume style analysis"
    tier4_query3 = f"top fashion bloggers and street style stars in {region}"
    tier4_query4 = f"emerging fashion designers to watch in {region} {year}"

    queries = [
        tier1_query,
        tier2_query,
        tier3_query1,
        tier3_query2,
        tier4_query1,
        tier4_query2,
    ]
    if region:
        queries.extend([tier4_query3, tier4_query4])

    logger.info(f"Generated {len(queries)} definitive, high-quality queries.")
    return queries


# --- DEFINITIVE FIX: Restoring the missing helper function ---
def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Breaks a long text into smaller, overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


async def _run_tasks_in_batches(
    tasks: Sequence[Coroutine], batch_size: int, delay_seconds: int
) -> List[Any]:
    """Runs a sequence of awaitable tasks in batches to respect API rate limits."""
    all_results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i : i + batch_size]
        logger.info(
            f"Running batch {i//batch_size + 1} of {(len(tasks) + batch_size - 1)//batch_size} with {len(batch)} tasks..."
        )
        batch_results = await asyncio.gather(*batch)
        all_results.extend(batch_results)
        if i + batch_size < len(tasks):
            logger.warning(
                f"Batch complete. Waiting for {delay_seconds} seconds to respect API rate limit..."
            )
            await asyncio.sleep(delay_seconds)
    return all_results


# --- Main Service Function (Corrected) ---------------------------------------
async def run_creative_process(
    season: Optional[str],
    year: Optional[int],
    theme_hint: Optional[str],
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
):
    """
    Executes the full workflow, using an "intelligent funnel" to prepare
    the creative brief with validation, smart defaults, and auto-location.
    """
    logger.info(f"--- Received Raw Creative Brief ---")

    # --- The Intelligent Funnel (Now correctly located inside the service) ---
    if not theme_hint or not theme_hint.strip():
        logger.critical(
            "Halting process: 'THEME_HINT' could not be extracted from the user's passage."
        )
        return

    if not season:
        current_month = datetime.now().month
        season = "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
        logger.warning(f"No SEASON provided. Defaulting to current season: '{season}'")

    if not year:
        year = datetime.now().year
        logger.warning(f"No YEAR provided. Defaulting to current year: {year}")

    if not region:
        logger.info(
            "No region provided in brief. Attempting automatic location detection..."
        )
        region = get_location_from_ip()
        if not region:
            logger.warning(
                "Could not determine location automatically. Proceeding with a global search."
            )

    brief = {
        "season": season,
        "year": year,
        "theme_hint": theme_hint,
        "target_audience": target_audience,
        "region": region,
    }

    logger.info(f"--- Final Creative Brief Prepared ---")
    logger.info(f"Season: {brief['season']}, Year: {brief['year']}")
    logger.info(f"Theme: '{brief['theme_hint']}'")
    if brief["target_audience"]:
        logger.info(f"Audience: {brief['target_audience']}")
    if brief["region"]:
        logger.info(f"Region: {brief['region']}")

    composite_key = " | ".join([str(v) for v in brief.values() if v is not None])
    cached_report_json = cache_service.check_cache(composite_key)

    if cached_report_json:
        logger.warning(
            "--- Workflow Bypassed: Using Semantically Similar Cached Report ---"
        )
        try:
            validated_report = FashionTrendReport(**json.loads(cached_report_json))
            output_utils.save_json_to_results(
                validated_report.model_dump(), config.TREND_REPORT_FILENAME
            )
            final_prompts = output_utils.generate_final_prompts(validated_report)
            output_utils.save_json_to_results(final_prompts, config.PROMPTS_FILENAME)
            logger.info("--- Cached Process Completed Successfully ---")
            return
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                f"Failed to process cached report: {e}. Proceeding with full workflow.",
                exc_info=True,
            )

    logger.info("--- Starting Full Research & Synthesis Workflow ---")

    # --- CORRECTED CALL ---
    # Now correctly calls the local private helper function.
    queries = _generate_search_queries(brief)

    scraped_documents = await research_client.gather_research_documents(queries)

    if not scraped_documents:
        logger.error("Halting process: No content was successfully scraped.")
        return

    logger.info(
        f"--- Starting Intelligent Summarization of {len(scraped_documents)} documents ---"
    )
    all_chunks = []
    for doc in scraped_documents:
        chunks = _chunk_text(doc, chunk_size=20000, overlap=1000)
        all_chunks.extend(chunks)
    logger.info(
        f"Broken down {len(scraped_documents)} documents into {len(all_chunks)} total chunks for summarization."
    )

    summarization_tasks = [
        llm_client.generate_text_async(
            prompt_library.SUMMARIZATION_PROMPT_TEMPLATE.format(document_text=chunk)
        )
        for chunk in all_chunks
    ]
    summaries = await _run_tasks_in_batches(
        summarization_tasks, config.GEMINI_API_CONCURRENCY_LIMIT, 61
    )
    valid_summaries = [
        s for s in summaries if s and "No relevant information." not in s
    ]

    if not valid_summaries:
        logger.error("Halting process: Failed to generate any valid summaries.")
        return

    research_context = "\n\n--- DOCUMENT CHUNK SUMMARY ---\n\n".join(valid_summaries)
    logger.info(
        f"Successfully generated {len(valid_summaries)} summaries from {len(all_chunks)} chunks."
    )

    final_prompt = prompt_library.ITEMIZED_REPORT_PROMPT.format(
        research_context=research_context,
        season=brief["season"],
        year=brief["year"],
        region=brief["region"],
    )
    json_response = llm_client.generate_structured_json(final_prompt)

    if not json_response:
        logger.error("Halting process: Failed to get an initial response from the LLM.")
        return

    validated_report = None
    try:
        validated_report = FashionTrendReport(**json.loads(json_response))
        logger.info("Successfully validated LLM response on the first attempt!")
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            f"Initial validation failed: {e}. Initiating self-correction loop."
        )
        correction_prompt = prompt_library.JSON_CORRECTION_PROMPT.format(
            broken_json=json_response, validation_errors=str(e)
        )
        corrected_json_response = llm_client.generate_structured_json(correction_prompt)
        if corrected_json_response:
            try:
                validated_report = FashionTrendReport(
                    **json.loads(corrected_json_response)
                )
                logger.info(
                    "Successfully validated LLM response after self-correction!"
                )
            except (json.JSONDecodeError, ValidationError) as final_e:
                logger.error(
                    f"Self-correction also failed validation. Final error: {final_e}",
                    exc_info=True,
                )
                output_utils.save_json_to_results(
                    {"error": "Original invalid JSON", "content": json_response},
                    "invalid_llm_response.json",
                )
                output_utils.save_json_to_results(
                    {
                        "error": "Failed correction attempt",
                        "content": corrected_json_response,
                    },
                    "failed_correction_response.json",
                )
        else:
            logger.error("LLM failed to provide a corrected JSON response.")
            output_utils.save_json_to_results(
                {"error": "Original invalid JSON", "content": json_response},
                "invalid_llm_response.json",
            )

    if validated_report:
        output_utils.save_json_to_results(
            validated_report.model_dump(), config.TREND_REPORT_FILENAME
        )
        cache_service.add_to_cache(composite_key, validated_report.model_dump_json())
        final_prompts = output_utils.generate_final_prompts(validated_report)
        output_utils.save_json_to_results(final_prompts, config.PROMPTS_FILENAME)
        logger.info(
            f"--- Creative Process for {brief['season']} {brief['year']}: '{brief['theme_hint']}' Completed Successfully ---"
        )
    else:
        logger.critical(
            "Halting process: Reached end of workflow without a validated report."
        )
