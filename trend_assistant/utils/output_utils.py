"""
Utility functions for handling and saving the final application outputs.
"""

import json
import os
from typing import Dict, Any

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


def generate_final_prompts(report: FashionTrendReport) -> Dict[str, Any]:
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
