"""
Client for interacting with the Google Generative AI (Gemini) API.

This module encapsulates all the logic required to send prompts to the
Gemini model and receive responses. It utilizes the modern, unified
Google GenAI SDK with a client-based approach.
"""

import asyncio
from typing import Optional, List
from google import genai
from google.genai.types import GenerateContentConfig, EmbedContentConfig
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


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generates a vector embedding for a given text string with robust error handling.
    """
    if client is None:
        logger.error(
            "Cannot generate embedding because GenAI client is not initialized."
        )
        return None

    logger.info(f"Generating embedding for text: '{text[:50]}...'")
    try:
        result = client.models.embed_content(
            model=config.EMBEDDING_MODEL_NAME,
            contents=[text],
            config=EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )

        # --- CRITICAL FIX: Defensive check for a valid response ---
        # This prevents the "None is not subscriptable" or "AttributeError" crash.
        # It checks if the result exists AND if the embeddings list is not empty.
        if result and result.embeddings:
            logger.info("Successfully generated embedding.")
            return result.embeddings[0].values
        else:
            # This case handles a successful API call that returns an empty response.
            logger.warning(
                "Embedding generation call succeeded but returned no embeddings."
            )
            return None

    except Exception as e:
        # This case handles all other errors (network, API key, etc.).
        logger.error(
            f"An error occurred during embedding generation: {e}", exc_info=True
        )
        return None


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
    """Asynchronously generates plain text by running the sync call in a thread."""
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
