"""
Client for interacting with the Google Generative AI (Gemini) API.
(Fixed version with proper authentication)
"""

import asyncio
import os
from typing import Optional, List
from google import genai
from google.genai.types import GenerateContentConfig, EmbedContentConfig
from .. import config
from ..utils.logger import logger

# --- PROPER AUTHENTICATION FIX ---
# The Google GenAI library automatically picks up API keys from environment variables.
# It looks for GOOGLE_API_KEY first, then other variants.
# We need to ensure the correct key is set in the environment.


def _setup_api_key():
    """Ensure the correct API key is set in the environment."""
    try:
        # Clear any conflicting keys and set the one we want
        if hasattr(config, "GEMINI_API_KEY") and config.GEMINI_API_KEY:
            # Set the key that the library expects
            os.environ["GOOGLE_API_KEY"] = config.GEMINI_API_KEY
            # Clear any other variants to avoid conflicts
            for key in ["GEMINI_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"]:
                if key in os.environ and key != "GOOGLE_API_KEY":
                    del os.environ[key]
            logger.info("Set GOOGLE_API_KEY from config.GEMINI_API_KEY")
        elif "GOOGLE_API_KEY" not in os.environ:
            logger.error("No API key found in config.GEMINI_API_KEY or environment")
            return False
        return True
    except Exception as e:
        logger.error(f"Error setting up API key: {e}")
        return False


# Set up the API key and initialize client
try:
    if _setup_api_key():
        client = genai.Client()
        logger.info(
            "Google GenAI client initialized successfully with correct API key."
        )
    else:
        client = None
        logger.critical("Failed to set up API key for GenAI client")
except Exception as e:
    logger.critical(
        f"CRITICAL: Failed to initialize Google GenAI client: {e}",
        exc_info=True,
    )
    client = None


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generates a vector embedding for a given text string using the
    correctly configured client instance.
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

        if result and result.embeddings:
            logger.info("Successfully generated embedding.")
            return result.embeddings[0].values
        else:
            logger.warning(
                "Embedding generation call succeeded but returned no embeddings."
            )
            return None

    except Exception as e:
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
