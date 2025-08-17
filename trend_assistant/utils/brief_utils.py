"""
Utility functions for handling and preparing the creative brief.

This module is responsible for the "Phase 0" of the workflow: deconstructing
the user's natural language request into a structured format that the main
workflow service can understand and process.
"""

import json
from typing import Optional, Dict

from ..clients import llm_client
from ..prompts import prompt_library
from ..utils.logger import logger


def deconstruct_brief_with_ai(user_passage: str) -> Optional[Dict]:
    """
    Uses an LLM to parse a natural language passage into a structured brief.
    """
    logger.info("Deconstructing user's natural language brief with AI...")

    prompt = prompt_library.BRIEF_DECONSTRUCTION_PROMPT.format(
        user_passage=user_passage
    )

    json_response = llm_client.generate_structured_json(prompt)

    if not json_response:
        logger.error(
            "AI failed to deconstruct the user's brief. The model returned an empty response."
        )
        return None

    try:
        brief_data = json.loads(json_response)
        logger.info(f"Successfully deconstructed brief: {brief_data}")
        return brief_data
    except json.JSONDecodeError:
        logger.error(
            f"AI returned an invalid JSON object during brief deconstruction. Response: {json_response[:500]}..."
        )
        return None
