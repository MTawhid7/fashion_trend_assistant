"""
Core Workflow Service for the Fashion Trend Assistant.
(Upgraded with a global-first, context-aware search strategy)
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Coroutine, Optional, Sequence

from . import cache_service
from .. import config
from ..clients import llm_client, research_client
from ..models.trend_models import FashionTrendReport
from ..prompts import prompt_library
from ..utils.logger import logger

# --- Helper Functions --------------------------------------------------------


def _generate_search_queries(
    season: str,
    year: int,
    theme_hint: str,
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
) -> List[str]:
    """
    Creates a sophisticated, multi-tiered list of search queries that is
    flexible and now includes queries specifically targeting key garments.
    """
    logger.info(
        "Generating a flexible, context-aware set of professional search queries..."
    )

    audience_query = f" for {target_audience}" if target_audience else ""
    region_search_query = f" in {region}" if region else ""

    # --- Tier 1: High-Fashion & Regional Runway Analysis ---
    tier1_queries = [
        f"Vogue {region_search_query} {season} {year} runway trend report",
        f"WWD {season} {year} {region_search_query} runway analysis {theme_hint}",
        f"Business of Fashion {season} {year} {region_search_query} collection reviews",
        f"Elle {region_search_query} {season} {year} fashion week highlights",
    ]

    # --- Tier 2: Global Trend Forecasting & Material Innovation ---
    tier2_queries = [
        f"WGSN {season} {year} key trends {theme_hint}",
        f"Trendstop forecast {season} {year} {theme_hint}",
        f"Pantone Color Institute fashion color trend report {season} {year}",
        f"Première Vision {season} {year} fabric and textile news",
    ]

    # --- NEW TIER 3: Specific Garment & Item Analysis ---
    # This tier is designed to find the specific "nouns" of the fashion trend.
    tier3_queries = [
        f"'{theme_hint}' key pieces {season} {year}{region_search_query}",
        f"must-have garments {season} {year} fashion {region_search_query}",
        f"top fashion items {audience_query}{region_search_query} {year}",
    ]

    # --- Tier 4: Cultural & Street-Level Inspiration ---
    tier4_queries = [
        f"'{theme_hint}' aesthetic in contemporary art and fashion{region_search_query}",
        f"latest street style {theme_hint}{region_search_query}{audience_query}",
        f"top fashion influencers {region_search_query} {year}",
    ]

    queries = tier1_queries + tier2_queries + tier3_queries + tier4_queries
    logger.info(f"Generated {len(queries)} flexible queries across 4 strategic tiers.")
    return queries


def _save_json_to_results(data: Dict[str, Any], filename: str) -> bool:
    """Saves a dictionary to a JSON file in the results directory."""
    try:
        config.RESULTS_DIR.mkdir(exist_ok=True)
        file_path = os.path.join(config.RESULTS_DIR, filename)
        logger.info(f"Saving data to '{file_path}'...")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved file: {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON file '{filename}': {e}", exc_info=True)
        return False


def _generate_final_prompts(report: FashionTrendReport) -> Dict[str, Any]:
    """Generates the final image prompts from the validated trend report."""
    logger.info("--- Starting Prompt Generation Phase ---")
    if not report.detailed_key_pieces:
        logger.error("Cannot generate prompts because 'detailed_key_pieces' is empty.")
        return {}
    all_prompts = {}
    model_style = (
        report.influential_models[0] if report.influential_models else "a fashion model"
    )
    for piece in report.detailed_key_pieces:
        logger.info(f"Generating prompts for key piece: '{piece.key_piece_name}'")
        main_fabric = (
            piece.fabrics[0].material if piece.fabrics else "a high-quality fabric"
        )
        main_color = piece.colors[0].name if piece.colors else "a core color"
        silhouette = (
            piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
        )
        piece_prompts = {
            "inspiration_board": prompt_library.INSPIRATION_BOARD_PROMPT_TEMPLATE.format(
                theme=report.overarching_theme,
                key_piece_name=piece.key_piece_name,
                cultural_drivers=", ".join(report.cultural_drivers),
                model_style=model_style,
            ),
            "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                key_piece_name=piece.key_piece_name,
                fabric_names=", ".join([f.material for f in piece.fabrics]),
                color_names=", ".join([c.name for c in piece.colors]),
                details_trims=", ".join(piece.details_trims),
            ),
            "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                model_style=model_style,
                key_piece_name=piece.key_piece_name,
                main_color=main_color,
                main_fabric=main_fabric,
                silhouette=silhouette,
                details_trims=", ".join(piece.details_trims),
            ),
        }
        all_prompts[piece.key_piece_name] = piece_prompts
    logger.info("--- Prompt Generation Phase Complete ---")
    return all_prompts


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


# --- Main Service Function (UPGRADED) ---------------------------------------


async def run_creative_process(
    season: Optional[str],
    year: Optional[int],
    theme_hint: Optional[str],
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
):
    """
    Executes the full workflow, now with input validation and smart defaults.
    """
    logger.info(f"--- Received New Creative Brief ---")

    # --- STEP 1: VALIDATE AND SET DEFAULTS ---

    # The THEME_HINT is the only truly essential creative input.
    if not theme_hint or not theme_hint.strip():
        logger.critical(
            "Halting process: 'THEME_HINT' cannot be empty. Please provide a creative direction."
        )
        return

    # For SEASON, provide a smart default based on the current month.
    if not season:
        current_month = datetime.now().month
        # Spring/Summer season roughly from April to September
        if 4 <= current_month <= 9:
            season = "Spring/Summer"
        else:
            season = "Fall/Winter"
        logger.warning(f"No SEASON provided. Defaulting to current season: '{season}'")

    # For YEAR, provide a smart default based on the current year.
    if not year:
        year = datetime.now().year
        logger.warning(f"No YEAR provided. Defaulting to current year: {year}")

    # --- The rest of the function proceeds with validated/defaulted inputs ---

    logger.info(
        f"--- Starting New Creative Process for {season} {year}: '{theme_hint}' ---"
    )
    if target_audience:
        logger.info(f"Target Audience: {target_audience}")
    if region:
        logger.info(f"Region: {region}")

    cache_key = f"{theme_hint}_{region or 'global'}_{target_audience or 'all'}"
    cached_report_json = cache_service.check_cache(cache_key)

    if cached_report_json:
        logger.warning(
            "--- Workflow Bypassed: Using Semantically Similar Cached Report ---"
        )
        try:
            report_data = json.loads(cached_report_json)
            validated_report = FashionTrendReport(**report_data)
            _save_json_to_results(
                validated_report.model_dump(), config.TREND_REPORT_FILENAME
            )
            final_prompts = _generate_final_prompts(validated_report)
            _save_json_to_results(final_prompts, config.PROMPTS_FILENAME)
            logger.info("--- Cached Process Completed Successfully ---")
            return
        except (json.JSONDecodeError, Exception) as e:
            logger.error(
                f"Failed to process cached report. Error: {e}. Proceeding with full workflow.",
                exc_info=True,
            )

    logger.info("--- Starting Full Research & Synthesis Workflow ---")

    queries = _generate_search_queries(
        season, year, theme_hint, target_audience, region
    )
    scraped_documents = await research_client.gather_research_documents(queries)

    if not scraped_documents:
        logger.error("Halting process: No content was successfully scraped.")
        return

    logger.info(
        f"--- Starting Intelligent Summarization of {len(scraped_documents)} documents ---"
    )
    summarization_tasks = [
        llm_client.generate_text_async(
            prompt_library.SUMMARIZATION_PROMPT_TEMPLATE.format(
                document_text=doc[:150000]
            )
        )
        for doc in scraped_documents
    ]
    summaries = await _run_tasks_in_batches(
        tasks=summarization_tasks,
        batch_size=config.GEMINI_API_CONCURRENCY_LIMIT,
        delay_seconds=61,
    )
    valid_summaries = [
        s for s in summaries if s and "No relevant information." not in s
    ]

    if not valid_summaries:
        logger.error(
            "Halting process: Failed to generate any valid summaries from the research."
        )
        return

    research_context = "\n\n--- DOCUMENT SUMMARY ---\n\n".join(valid_summaries)
    logger.info(f"Successfully generated {len(valid_summaries)} summaries.")

    logger.info("--- Starting Final Data Synthesis Phase ---")
    final_prompt = prompt_library.ITEMIZED_REPORT_PROMPT.format(
        research_context=research_context, season=season, year=year
    )

    json_response = llm_client.generate_structured_json(final_prompt)

    if not json_response:
        logger.error(
            "Halting process: Failed to get a valid JSON response from the LLM."
        )
        return

    try:
        report_data = json.loads(json_response)
        validated_report = FashionTrendReport(**report_data)
        logger.info("Successfully validated final LLM response against Pydantic model.")
        _save_json_to_results(
            validated_report.model_dump(), config.TREND_REPORT_FILENAME
        )

        # Add the new report to the cache using the more specific key.
        cache_service.add_to_cache(cache_key, validated_report.model_dump_json())

    except (json.JSONDecodeError, Exception) as e:
        logger.error(
            f"Halting process: Final LLM response failed validation. Error: {e}",
            exc_info=True,
        )
        config.RESULTS_DIR.mkdir(exist_ok=True)
        with open(
            os.path.join(config.RESULTS_DIR, "invalid_llm_response.json"), "w"
        ) as f:
            f.write(json_response)
        return

    final_prompts = _generate_final_prompts(validated_report)
    _save_json_to_results(final_prompts, config.PROMPTS_FILENAME)

    logger.info(
        f"--- Creative Process for {season} {year}: '{theme_hint}' Completed Successfully ---"
    )
