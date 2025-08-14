"""
Client for interacting with the Google Generative AI (Gemini) API.

This module encapsulates all the logic required to send prompts to the
Gemini model and receive responses. It utilizes the modern, unified
Google GenAI SDK with a client-based approach.
"""

import asyncio
from typing import Optional
from google import genai
from google.genai.types import GenerateContentConfig
from .. import config
from ..utils.logger import logger

try:
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    logger.info("Google GenAI client initialized successfully.")
except Exception as e:
    logger.critical(
        f"CRITICAL: Failed to initialize Google GenAI client: {e}", exc_info=True
    )
    client = None


def _sync_generate_text(prompt: str) -> Optional[str]:
    """Internal synchronous function for generating plain text."""
    if client is None:
        logger.error("Cannot generate content because GenAI client is not initialized.")
        return None
    try:
        model_id = f"models/{config.GEMINI_MODEL_NAME}"
        response = client.models.generate_content(model=model_id, contents=prompt)
        return response.text
    except Exception as e:
        logger.error(
            f"An error occurred during a sync text generation call: {e}", exc_info=True
        )
        return None


async def generate_text_async(prompt: str) -> Optional[str]:
    """
    Asynchronously generates plain text by running the sync call in a thread.
    The semaphore logic has been removed as rate-limiting is now handled
    by the calling service's batching mechanism.
    """
    logger.info("Submitting async text generation task to thread pool...")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_generate_text, prompt)


def generate_structured_json(prompt: str) -> Optional[str]:
    """Generates a structured JSON response from the Gemini model."""
    if client is None:
        logger.error("Cannot generate content because GenAI client is not initialized.")
        return None
    model_id = f"models/{config.GEMINI_MODEL_NAME}"
    logger.info(f"Sending prompt to Gemini model '{model_id}' for JSON generation...")
    try:
        generation_config = GenerateContentConfig(
            response_mime_type="application/json", temperature=0.2
        )
        response = client.models.generate_content(
            model=model_id, contents=prompt, config=generation_config
        )
        logger.info("Successfully received structured response from Gemini API.")
        return response.text
    except Exception as e:
        logger.error(
            f"An error occurred while calling the Gemini API for JSON: {e}",
            exc_info=True,
        )
        return None
