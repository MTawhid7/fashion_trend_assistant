"""
Core Workflow Service for the Fashion Trend Assistant.
(Definitive version with modular helpers and self-correction)
"""

import json
import os
import asyncio
from typing import List, Any, Coroutine, Optional, Sequence
from pydantic import ValidationError

from . import cache_service
from .. import config
from ..clients import llm_client, research_client
from ..models.trend_models import FashionTrendReport
from ..prompts import prompt_library
from ..utils.logger import logger
from ..utils import brief_utils, output_utils


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


async def run_creative_process(
    season: Optional[str],
    year: Optional[int],
    theme_hint: Optional[str],
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
):
    """Executes the full workflow, orchestrating calls to various services and utilities."""

    brief = brief_utils.prepare_creative_brief(
        season, year, theme_hint, target_audience, region
    )
    if not brief:
        return

    logger.info(
        f"--- Starting New Creative Process for {brief['season']} {brief['year']}: '{brief['theme_hint']}' ---"
    )
    if brief["target_audience"]:
        logger.info(f"Target Audience: {brief['target_audience']}")
    if brief["region"]:
        logger.info(f"Region: {brief['region']}")

    composite_key = " | ".join([str(v) for v in brief.values()])
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

    queries = brief_utils.generate_search_queries(brief)
    scraped_documents = await research_client.gather_research_documents(queries)

    if not scraped_documents:
        logger.error("Halting process: No content was successfully scraped.")
        return

    summarization_tasks = [
        llm_client.generate_text_async(
            prompt_library.SUMMARIZATION_PROMPT_TEMPLATE.format(
                document_text=doc[:150000]
            )
        )
        for doc in scraped_documents
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

    research_context = "\n\n--- DOCUMENT SUMMARY ---\n\n".join(valid_summaries)

    final_prompt = prompt_library.ITEMIZED_REPORT_PROMPT.format(
        research_context=research_context, season=brief["season"], year=brief["year"]
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
                # --- DEFINITIVE FIX: Save both error files for debugging ---
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
            # --- DEFINITIVE FIX: Save the original error file for debugging ---
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
