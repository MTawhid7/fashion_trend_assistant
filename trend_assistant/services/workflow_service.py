"""
Core Workflow Service for the Fashion Trend Assistant.
"""

import json
import os
import asyncio
from typing import Dict, List, Any, Coroutine

from .. import config
from ..clients import llm_client, research_client
from ..models.trend_models import FashionTrendReport
from ..prompts import prompt_library
from ..utils.logger import logger

# --- Helper Functions --------------------------------------------------------


def _generate_search_queries(season: str, year: int, theme_hint: str) -> List[str]:
    """Creates a list of targeted search queries based on the initial brief."""
    logger.info("Generating dynamic search queries...")
    queries = [
        f"WGSN {season} {year} fashion trends {theme_hint}",
        f"Vogue Runway {season} {year} trend report analysis",
        f"Business of Fashion {season} {year} materials and textiles {theme_hint}",
        f"Dazed Digital {season} {year} {theme_hint} aesthetic",
        f"latest street style {theme_hint}",
    ]
    logger.info(f"Generated {len(queries)} queries.")
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

    # CRITICAL SAFEGUARD: Check if the key pieces list is empty.
    if not report.detailed_key_pieces:
        logger.error(
            "Cannot generate prompts because the 'detailed_key_pieces' list in the report is empty. Check the synthesized JSON."
        )
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
    tasks: List[Coroutine], batch_size: int, delay_seconds: int
) -> List[Any]:
    """Runs a list of awaitable tasks in batches to respect API rate limits."""
    all_results = []
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i : i + batch_size]
        logger.info(
            f"Running batch {i//batch_size + 1} of {len(tasks)//batch_size + 1} with {len(batch)} tasks..."
        )

        batch_results = await asyncio.gather(*batch)
        all_results.extend(batch_results)

        if i + batch_size < len(tasks):
            logger.warning(
                f"Batch complete. Waiting for {delay_seconds} seconds to respect API rate limit..."
            )
            await asyncio.sleep(delay_seconds)

    return all_results


# --- Main Service Function ---------------------------------------------------


async def run_creative_process(season: str, year: int, theme_hint: str):
    """Executes the full workflow with intelligent summarization and batched rate limiting."""
    logger.info(
        f"--- Starting New Creative Process for {season} {year}: '{theme_hint}' ---"
    )

    queries = _generate_search_queries(season, year, theme_hint)
    scraped_documents = await research_client.gather_research_documents(queries)

    if not scraped_documents:
        logger.error(
            "Halting process: No content was successfully scraped from any URLs."
        )
        return

    logger.info(
        f"--- Starting Intelligent Summarization of {len(scraped_documents)} documents ---"
    )

    summarization_tasks = []
    for doc in scraped_documents:
        prompt = prompt_library.SUMMARIZATION_PROMPT_TEMPLATE.format(
            document_text=doc[:150000]
        )
        summarization_tasks.append(llm_client.generate_text_async(prompt))

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
    logger.info(
        f"Successfully generated {len(valid_summaries)} summaries. Total context length: {len(research_context)}"
    )

    logger.info("--- Starting Final Data Synthesis Phase ---")
    final_prompt = prompt_library.ITEMIZED_REPORT_PROMPT.format(
        research_context=research_context, season=season, year=year
    )

    json_response = llm_client.generate_structured_json(final_prompt)

    if not json_response:
        logger.error(
            "Halting process: Failed to get a valid JSON response from the LLM for the final report."
        )
        return

    try:
        report_data = json.loads(json_response)
        validated_report = FashionTrendReport(**report_data)
        logger.info("Successfully validated final LLM response against Pydantic model.")
        _save_json_to_results(
            validated_report.model_dump(), config.TREND_REPORT_FILENAME
        )
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
