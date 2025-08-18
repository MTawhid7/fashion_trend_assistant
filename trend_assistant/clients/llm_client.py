"""
Client for interacting with the Google Generative AI (Gemini) API.
(2025 Updated version - Fixed configuration parameter passing)
"""

import asyncio
import os
import time
import random
from typing import Optional, List, Union, Callable, Any, Dict
from google import genai
from google.genai import types
from .. import config
from ..utils.logger import logger


def _setup_api_key() -> bool:
    """Ensure the correct API key is set in the environment."""
    try:
        if hasattr(config, "GEMINI_API_KEY") and config.GEMINI_API_KEY:
            os.environ["GOOGLE_API_KEY"] = config.GEMINI_API_KEY
            logger.info("Set GOOGLE_API_KEY from config")
        elif "GOOGLE_API_KEY" not in os.environ:
            logger.error("No API key found in config or environment")
            return False
        return True
    except Exception as e:
        logger.error(f"Error setting up API key: {e}")
        return False


# Set up the API key and initialize client
client: Optional[genai.Client] = None
try:
    if _setup_api_key():
        client = genai.Client()
        logger.info("Official Google GenAI client initialized successfully.")
    else:
        client = None
        logger.critical("Failed to set up API key for GenAI client")
except Exception as e:
    logger.critical(
        f"CRITICAL: Failed to initialize Google GenAI client: {e}", exc_info=True
    )
    client = None


def _should_retry(error: Exception) -> bool:
    """Determine if an error is retryable based on API patterns."""
    error_str = str(error).lower()
    retryable_codes = ["500", "502", "503", "504", "429", "internal"]
    retryable_messages = [
        "internal error",
        "internal server error",
        "timeout",
        "temporarily unavailable",
        "rate limit",
        "quota exceeded",
        "service unavailable",
        "backend error",
        "an internal error has occurred",
    ]
    return any(code in error_str for code in retryable_codes) or any(
        msg in error_str for msg in retryable_messages
    )


def _calculate_backoff_delay(
    attempt: int, base_delay: float = 2.0, max_delay: float = 120.0
) -> float:
    """Calculate exponential backoff delay with jitter."""
    delay = base_delay * (2**attempt)
    delay = min(delay, max_delay)
    jitter = random.uniform(0.1, 0.4) * delay
    return delay + jitter


def _retry_with_backoff(
    func: Callable[..., Any], max_retries: int = 5, base_delay: float = 2.0
) -> Callable[..., Any]:
    """Decorator for retry logic with exponential backoff."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exception: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        f"Successfully recovered after {attempt} retries for {func.__name__}"
                    )
                return result
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    logger.error(
                        f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                    )
                    break
                if not _should_retry(e):
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    break
                delay = _calculate_backoff_delay(attempt, base_delay)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError(
                f"Function {func.__name__} failed without raising an exception"
            )

    return wrapper


def _validate_model_name(model_name: str) -> str:
    """Validates the model name format, ensuring it doesn't have prefixes."""
    if model_name.startswith("models/"):
        corrected = model_name.split("models/", 1)[1]
        logger.info(f"Corrected model name from '{model_name}' to '{corrected}'")
        return corrected
    return model_name


def _get_default_model() -> str:
    """Get the default model name, preferring Gemini 2.5 models."""
    configured_model = getattr(config, "GEMINI_MODEL_NAME", None)
    if configured_model:
        return configured_model

    # Default to Gemini 2.5 Flash as it's the best price-performance model
    return "gemini-2.5-flash"


def generate_embedding(text: str, max_retries: int = 5) -> Optional[List[float]]:
    """Generates a vector embedding using the latest embedding model."""
    if client is None:
        logger.error(
            "Cannot generate embedding because GenAI client is not initialized."
        )
        return None
    logger.info(f"Generating embedding for text: '{text[:50]}...'")

    @_retry_with_backoff
    def _generate_embedding_with_retry() -> Optional[List[float]]:
        if client is None:
            raise RuntimeError("Client is not initialized")
        embedding_model = getattr(config, "EMBEDDING_MODEL_NAME", "text-embedding-004")
        result = client.models.embed_content(
            model=embedding_model,
            contents=[text],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        if result and result.embeddings and result.embeddings[0].values:
            return result.embeddings[0].values
        return None

    try:
        embedding = _generate_embedding_with_retry()
        if embedding:
            logger.info("Successfully generated embedding.")
        return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding after retries: {e}", exc_info=True)
        return None


def _sync_generate_text(prompt: str, max_retries: int = 5) -> Optional[str]:
    """Internal synchronous function for generating plain text."""
    if client is None:
        logger.error("Cannot generate content because GenAI client is not initialized.")
        return None

    @_retry_with_backoff
    def _generate_text_with_retry() -> Optional[str]:
        if client is None:
            raise RuntimeError("Client is not initialized")
        model_name = _get_default_model()
        validated_model = _validate_model_name(model_name)
        response = client.models.generate_content(
            model=validated_model, contents=prompt
        )
        return response.text

    try:
        return _generate_text_with_retry()
    except Exception as e:
        logger.error(f"Failed to generate text after retries: {e}", exc_info=True)
        return None


async def generate_text_async(prompt: str, max_retries: int = 5) -> Optional[str]:
    """Asynchronously generates plain text using the async SDK."""
    if client is None:
        logger.error("Cannot generate content because GenAI client is not initialized.")
        return None
    logger.info("Generating text asynchronously...")
    try:
        model_name = _get_default_model()
        validated_model = _validate_model_name(model_name)
        response = await client.aio.models.generate_content(
            model=validated_model, contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Failed to generate text asynchronously: {e}", exc_info=True)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, _sync_generate_text, prompt, max_retries
        )


def generate_structured_json(
    prompt: str, max_retries: int = 5, temperature: float = 0.1
) -> Optional[str]:
    """Generates structured JSON using the official GenAI SDK."""
    if client is None:
        logger.error("Cannot generate content because GenAI client is not initialized.")
        return None

    model_name = _get_default_model()
    validated_model = _validate_model_name(model_name)

    logger.info(
        f"Sending prompt to Gemini model '{validated_model}' for JSON generation..."
    )

    @_retry_with_backoff
    def _generate_json_with_retry() -> Optional[str]:
        if client is None:
            raise RuntimeError("Client is not initialized")

        try:
            # Create safety settings using the proper enum values
            safety_settings = [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]

            # Create the generation configuration using types.GenerateContentConfig
            generation_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
                top_p=0.8,
                top_k=40,
                response_mime_type="application/json",
                safety_settings=safety_settings,
            )

            # Make the API call with proper config parameter
            response = client.models.generate_content(
                model=validated_model, contents=prompt, config=generation_config
            )

            if not response or not response.text:
                raise RuntimeError("Empty response from API")
            return response.text

        except Exception as e:
            error_details = {
                "model": validated_model,
                "temperature": temperature,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(f"API call failed with details: {error_details}")
            raise e

    try:
        result = _generate_json_with_retry()
        if result:
            logger.info("Successfully received structured response from Gemini API.")
        return result
    except Exception as e:
        logger.error(f"Failed to generate JSON after retries: {e}", exc_info=True)
        return None


def check_api_health() -> bool:
    """Check if the Gemini API is accessible."""
    if client is None:
        logger.error("Client not initialized for health check")
        return False
    try:
        model_name = _get_default_model()
        validated_model = _validate_model_name(model_name)
        response = client.models.generate_content(
            model=validated_model, contents="Test connection. Respond with 'OK'."
        )
        if response and response.text:
            logger.info(f"API health check passed for model {validated_model}")
            return True
        else:
            logger.error("API health check failed - no response")
            return False
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return False


def get_model_info() -> Dict[str, Any]:
    """Get information about the current model configuration."""
    model_name = _get_default_model()
    validated_model = _validate_model_name(model_name)
    model_specs = {
        "gemini-2.5-pro": {
            "input_token_limit": 2048000,
            "output_token_limit": 65536,
            "supports_json": True,
            "supports_function_calling": True,
            "supports_thinking": True,
        },
        "gemini-2.5-flash": {
            "input_token_limit": 1048576,
            "output_token_limit": 65536,
            "supports_json": True,
            "supports_function_calling": True,
            "supports_thinking": True,
        },
        "gemini-2.5-flash-lite": {
            "input_token_limit": 1048576,
            "output_token_limit": 65536,
            "supports_json": True,
            "supports_function_calling": True,
            "supports_thinking": False,
        },
    }
    return {
        "configured_model": getattr(config, "GEMINI_MODEL_NAME", "Not configured"),
        "validated_model": validated_model,
        "specifications": model_specs.get(validated_model, {}),
        "client_initialized": client is not None,
    }


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 180):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
        self.consecutive_successes = 0

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        current_time = time.time()
        if self.state == "OPEN":
            if (
                self.last_failure_time
                and current_time - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                recovery_time = self.recovery_timeout
                if self.last_failure_time:
                    recovery_time -= current_time - self.last_failure_time
                raise RuntimeError(
                    f"Circuit breaker is OPEN. Recovery in {recovery_time:.0f} seconds"
                )
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.consecutive_successes += 1
                if self.consecutive_successes >= 3:
                    self.state = "CLOSED"
                    self.failure_count = 0
                    self.consecutive_successes = 0
                    logger.info("Circuit breaker fully CLOSED after recovery")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = current_time
            self.consecutive_successes = 0
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker OPENED due to {self.failure_count} consecutive failures"
                )
            raise e


api_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=180)


def safe_api_call(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return api_circuit_breaker.call(func, *args, **kwargs)
