"""
Utility functions for handling and saving the final application outputs.
"""

import json
import os
from typing import Dict, Any, List

from .. import config
from ..models.trend_models import FashionTrendReport
from ..prompts import prompt_library
from ..utils.logger import logger


def save_json_to_results(data: Dict[str, Any], filename: str) -> bool:
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


def save_scraping_report(results: List[Dict[str, Any]]) -> bool:
    """
    Organizes all scraping results by outcome and saves them to a JSON file.
    """
    logger.info("Generating structured web scraping report with full content...")
    report = {"successful_scrapes": [], "partial_scrapes": [], "failed_scrapes": []}
    for res in results:
        status = res.get("status", "failed")
        if status == "success":
            report["successful_scrapes"].append(
                {
                    "url": res.get("url"),
                    "status": "success",
                    "content": res.get("content", ""),
                }
            )
        elif status == "partial":
            report["partial_scrapes"].append(
                {
                    "url": res.get("url"),
                    "status": "partial",
                    "reason": res.get("reason"),
                    "content": res.get("content", ""),
                }
            )
        else:
            report["failed_scrapes"].append(
                {
                    "url": res.get("url"),
                    "status": "failed",
                    "reason": res.get("reason", "Unknown failure"),
                }
            )
    return save_json_to_results(report, "scraping_report.json")


def generate_final_prompts(report: FashionTrendReport) -> Dict[str, Any]:
    """
    Generates the final image prompts from the validated trend report,
    pulling dynamic cultural and demographic data directly from the report.
    """
    logger.info("--- Starting Prompt Generation Phase ---")
    if not report.detailed_key_pieces:
        logger.error("Cannot generate prompts because 'detailed_key_pieces' is empty.")
        return {}

    all_prompts = {}
    model_style = (
        report.influential_models[0] if report.influential_models else "a fashion model"
    )
    region = getattr(report, "region", "the specified region")

    # --- DYNAMIC DATA EXTRACTION (NO HARDCODED MAPS) ---
    # The AI now provides the model ethnicity directly in the report.
    model_ethnicity = getattr(report, "target_model_ethnicity", "diverse")

    for piece in report.detailed_key_pieces:
        logger.info(f"Generating prompts for key piece: '{piece.key_piece_name}'")

        main_fabric = (
            piece.fabrics[0].material if piece.fabrics else "a high-quality fabric"
        )
        main_color = piece.colors[0].name if piece.colors else "a core color"
        silhouette = (
            piece.silhouettes[0] if piece.silhouettes else "a modern silhouette"
        )

        color_names = ", ".join([c.name for c in piece.colors])
        fabric_names = ", ".join([f.material for f in piece.fabrics])
        details_trims = ", ".join(piece.details_trims)

        # --- DYNAMIC DATA EXTRACTION (NO HARDCODED MAPS) ---
        # The AI now provides cultural patterns directly in the report for each piece.
        cultural_pattern = (
            piece.cultural_patterns[0]
            if piece.cultural_patterns
            else "a subtle geometric"
        )
        regional_context = f"traditional {cultural_pattern} patterns"

        key_accessories_list = []
        if report.accessories.get("Bags"):
            key_accessories_list.append(report.accessories["Bags"][0])
        if "Headscarves" in report.accessories.get("Other", []):
            key_accessories_list.append("a stylishly tied Headscarf")
        if report.accessories.get("Jewelry"):
            key_accessories_list.append(report.accessories["Jewelry"][0])
        key_accessories = ", ".join(key_accessories_list[:3])

        piece_prompts = {
            "inspiration_board": prompt_library.INSPIRATION_BOARD_PROMPT_TEMPLATE.format(
                theme=report.overarching_theme,
                key_piece_name=piece.key_piece_name,
                model_style=model_style,
                region=region,
                regional_context=regional_context,
                color_names=color_names,
                fabric_names=fabric_names,
            ),
            "mood_board": prompt_library.MOOD_BOARD_PROMPT_TEMPLATE.format(
                key_piece_name=piece.key_piece_name,
                region=region,
                fabric_names=fabric_names,
                culturally_specific_fabric=cultural_pattern,
                color_names=color_names,
                details_trims=details_trims,
                key_accessories=key_accessories,
                regional_context=regional_context,
            ),
            "final_garment": prompt_library.FINAL_GARMENT_PROMPT_TEMPLATE.format(
                model_style=model_style,
                model_ethnicity=model_ethnicity,
                key_piece_name=piece.key_piece_name,
                main_color=main_color,
                main_fabric=main_fabric,
                cultural_pattern=cultural_pattern,
                silhouette=silhouette,
                region=region,
                details_trims=details_trims,
            ),
        }
        all_prompts[piece.key_piece_name] = piece_prompts

    logger.info("--- Prompt Generation Phase Complete ---")
    return all_prompts
