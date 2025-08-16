"""
Core Workflow Service for the Fashion Trend Assistant.
(Final version with correct cache service integration)
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

# --- Helper Functions --------------------------------------------------------


def _generate_search_queries(
    season: str,
    year: int,
    theme_hint: str,
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
) -> List[str]:
    """
    Creates a definitive, multi-tiered list of search queries that is
    consolidated, refined, and globally aware.
    """
    logger.info(
        "Generating a definitive, consolidated set of professional search queries..."
    )

    audience_query = f" for {target_audience}" if target_audience else ""
    region_search_query = f" in {region}" if region else ""

    # --- Tier 1: Runway & Trend Analysis (Consolidated) ---
    # Combines the top 4 runway authorities into one powerful query.
    tier1_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR trend report OR collection review OR runway analysis) "
        f"(Vogue OR WWD OR Business of Fashion OR Elle){region_search_query}"
    )

    # --- Tier 2: Forecasting & Materials (Consolidated) ---
    # Combines the top 4 forecasting and material authorities.
    tier2_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR key trends OR forecast OR color OR fabric) "
        f"(WGSN OR Trendstop OR Pantone OR Première Vision)"
    )

    # --- Tier 3: Key Garments & Street Style (Consolidated & Refined) ---
    # Combines the search for specific items and how they are worn.
    tier3_query1 = f"({theme_hint} OR key pieces OR must-have items) {season} {year}{region_search_query}"
    tier3_query2 = (
        f"latest street style {theme_hint}{region_search_query}{audience_query}"
    )

    # --- Tier 4: Cultural Inspiration & Tastemakers (Refined) ---
    # Keeps the focus on finding unique, non-fashion inspiration and local influencers.
    tier4_query1 = (
        f"'{theme_hint}' aesthetic in contemporary art and fashion{region_search_query}"
    )
    tier4_query2 = f"'{theme_hint}' film and cinema costume style analysis"
    tier4_query3 = f"top fashion bloggers and street style stars in {region}"
    tier4_query4 = f"emerging fashion designers to watch in {region} {year}"

    # We only run the last two queries if a region is specified, as they are region-dependent.
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


# --- Main Service Function (Corrected) ---------------------------------------


async def run_creative_process(
    season: Optional[str],
    year: Optional[int],
    theme_hint: Optional[str],
    target_audience: Optional[str] = None,
    region: Optional[str] = None,
):
    """
    Executes the full workflow with input validation and a self-correction loop.
    """
    logger.info(f"--- Received New Creative Brief ---")

    if not theme_hint or not theme_hint.strip():
        logger.critical("Halting process: 'THEME_HINT' cannot be empty.")
        return

    if not season:
        current_month = datetime.now().month
        season = "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
        logger.warning(f"No SEASON provided. Defaulting to current season: '{season}'")

    if not year:
        year = datetime.now().year
        logger.warning(f"No YEAR provided. Defaulting to current year: {year}")

    logger.info(
        f"--- Starting New Creative Process for {season} {year}: '{theme_hint}' ---"
    )
    if target_audience:
        logger.info(f"Target Audience: {target_audience}")
    if region:
        logger.info(f"Region: {region}")

    # --- CORRECTED CACHE CHECK ---
    # The cache check now correctly passes only the theme_hint, as per the
    # definitive cache_service.py implementation.
    cached_report_json = cache_service.check_cache(theme_hint)

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
        logger.error("Halting process: Failed to get an initial response from the LLM.")
        return

    validated_report = None
    try:
        report_data = json.loads(json_response)
        validated_report = FashionTrendReport(**report_data)
        logger.info("Successfully validated LLM response on the first attempt!")
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            f"Initial validation failed: {e}. Initiating self-correction loop."
        )
        correction_prompt = prompt_library.JSON_CORRECTION_PROMPT.format(
            broken_json=json_response, validation_errors=str(e)
        )
        corrected_json_response = llm_client.generate_structured_json(correction_prompt)
        if not corrected_json_response:
            logger.error(
                "Halting process: LLM failed to provide a corrected JSON response."
            )
            config.RESULTS_DIR.mkdir(exist_ok=True)
            with open(
                os.path.join(config.RESULTS_DIR, "invalid_llm_response.json"), "w"
            ) as f:
                f.write(json_response)
            return
        try:
            report_data = json.loads(corrected_json_response)
            validated_report = FashionTrendReport(**report_data)
            logger.info("Successfully validated LLM response after self-correction!")
        except (json.JSONDecodeError, ValidationError) as final_e:
            logger.error(
                f"Halting process: Self-correction also failed validation. Final error: {final_e}",
                exc_info=True,
            )
            config.RESULTS_DIR.mkdir(exist_ok=True)
            with open(
                os.path.join(config.RESULTS_DIR, "invalid_llm_response.json"), "w"
            ) as f:
                f.write(json_response)
            with open(
                os.path.join(config.RESULTS_DIR, "failed_correction_response.json"), "w"
            ) as f:
                f.write(corrected_json_response)
            return

    if validated_report:
        _save_json_to_results(
            validated_report.model_dump(), config.TREND_REPORT_FILENAME
        )

        # --- CORRECTED CACHE ADD ---
        # The call to add_to_cache now correctly passes only the theme_hint and the report,
        # matching the definitive cache_service.py implementation.
        cache_service.add_to_cache(
            theme_hint=theme_hint, report_json=validated_report.model_dump_json()
        )

        final_prompts = _generate_final_prompts(validated_report)
        _save_json_to_results(final_prompts, config.PROMPTS_FILENAME)
        logger.info(
            f"--- Creative Process for {season} {year}: '{theme_hint}' Completed Successfully ---"
        )
    else:
        logger.critical(
            "Halting process: Reached end of workflow without a validated report."
        )
