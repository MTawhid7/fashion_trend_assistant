"""
Service for managing the ChromaDB semantic cache.

This module handles all interactions with the ChromaDB vector database. It is
responsible for initializing a persistent client, checking for semantically
similar documents (cache hits), and adding new documents to the cache
(on cache misses). This provides a long-term memory for the application.
"""

import chromadb
import hashlib
from typing import Optional

from .. import config
from ..clients import llm_client
from ..utils.logger import logger

# --- Module-level ChromaDB Initialization ------------------------------------
try:
    chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
    report_collection = chroma_client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME
    )
    logger.info(
        f"ChromaDB cache service initialized. Collection '{config.CHROMA_COLLECTION_NAME}' loaded/created."
    )
except Exception as e:
    logger.critical(
        f"CRITICAL: Failed to initialize ChromaDB client: {e}", exc_info=True
    )
    report_collection = None

# --- Public Service Functions ------------------------------------------------


def check_cache(theme_hint: str) -> Optional[str]:
    """
    Checks the cache for a semantically similar report with robust validation.

    Returns:
        The JSON string of a cached report if a sufficiently similar one is found,
        otherwise None, indicating a cache miss.
    """
    if report_collection is None:
        logger.error("ChromaDB collection not available. Skipping cache check.")
        return None

    logger.info(f"Checking semantic cache for theme hint: '{theme_hint}'")

    embedding = llm_client.generate_embedding(theme_hint)
    if not embedding:
        logger.warning(
            "Could not generate embedding for cache check. Proceeding as cache miss."
        )
        return None

    try:
        results = report_collection.query(query_embeddings=[embedding], n_results=1)
    except Exception as e:
        logger.error(f"An error occurred during ChromaDB query: {e}", exc_info=True)
        return None

    # --- DEFINITIVE FIX: Bulletproof validation of the results object ---
    try:
        # 1. Check if the results object itself is valid and has keys.
        if not results:
            logger.info("CACHE MISS: ChromaDB query returned an empty or None result.")
            return None

        # 2. Check if the essential lists exist
        required_keys = ["ids", "distances", "documents", "metadatas"]
        if not all(key in results for key in required_keys):
            logger.info(
                "CACHE MISS: Result object is missing one or more essential keys."
            )
            return None

        # 3. Check if all the lists are not empty and contain valid data
        if (
            not results["ids"]
            or len(results["ids"]) == 0
            or not results["distances"]
            or len(results["distances"]) == 0
            or not results["documents"]
            or len(results["documents"]) == 0
            or not results["metadatas"]
            or len(results["metadatas"]) == 0
        ):
            logger.info("CACHE MISS: One or more result lists are empty.")
            return None

        # 4. Check if the first result set (the inner list) exists and is not empty.
        if (
            len(results["ids"][0]) == 0
            or len(results["distances"][0]) == 0
            or len(results["documents"][0]) == 0
            or len(results["metadatas"][0]) == 0
        ):
            logger.info("CACHE MISS: No documents found for this query.")
            return None

        # 5. Check that the actual values are not None
        if (
            results["ids"][0][0] is None
            or results["distances"][0][0] is None
            or results["documents"][0][0] is None
            # Note: metadatas can legitimately be None, so we don't check it here
        ):
            logger.info("CACHE MISS: Found None values in critical result fields.")
            return None

        # 6. If all checks pass, it is now SAFE to access the values
        distance = results["distances"][0][0]
        document = results["documents"][0][0]
        metadata = results["metadatas"][0][0]

        if distance < config.CACHE_DISTANCE_THRESHOLD:
            cached_theme = metadata.get("theme_hint", "N/A") if metadata else "N/A"

            logger.warning(
                f"CACHE HIT! Found a similar report for theme '{cached_theme}' with distance {distance:.4f}."
            )
            return document
        else:
            logger.info(
                f"CACHE MISS. Closest document distance ({distance:.4f}) is above the threshold."
            )
            return None

    except (IndexError, TypeError, KeyError) as e:
        # This is a final safeguard against any unexpected structure.
        logger.error(
            f"Error while parsing ChromaDB results: {e}. Assuming cache miss.",
            exc_info=True,
        )
        return None


def add_to_cache(theme_hint: str, report_json: str):
    """
    Adds a newly generated report and its theme embedding to the cache.
    """
    if report_collection is None:
        logger.error("ChromaDB collection not available. Cannot add to cache.")
        return

    logger.info(f"Attempting to add new report to cache for theme: '{theme_hint}'")

    embedding = llm_client.generate_embedding(theme_hint)
    if not embedding:
        logger.error(
            "Could not generate embedding for new cache entry. Skipping add to cache."
        )
        return

    doc_id = hashlib.sha256(theme_hint.encode()).hexdigest()

    try:
        report_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[report_json],
            metadatas=[{"theme_hint": theme_hint}],
        )
        logger.info(f"Successfully added/updated report with ID {doc_id} in the cache.")
    except Exception as e:
        logger.error(
            f"Failed to add document to ChromaDB collection: {e}", exc_info=True
        )
