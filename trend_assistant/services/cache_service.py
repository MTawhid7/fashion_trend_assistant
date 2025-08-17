"""
Service for managing the ChromaDB semantic cache.
(Upgraded to use a composite key for multi-faceted semantic search)
"""

import chromadb
import hashlib
from typing import Optional

from .. import config
from ..clients import llm_client
from ..utils.logger import logger

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


def check_cache(composite_key: str) -> Optional[str]:
    """
    Checks the cache for a semantically similar report using a composite key.
    """
    if report_collection is None:
        return None
    logger.info(f"Checking semantic cache for composite key: '{composite_key}'")

    embedding = llm_client.generate_embedding(composite_key)
    if not embedding:
        return None

    try:
        results = report_collection.query(query_embeddings=[embedding], n_results=1)
    except Exception as e:
        logger.error(f"An error occurred during ChromaDB query: {e}", exc_info=True)
        return None

    try:
        # Check if results structure is valid and contains actual data
        if (
            not results
            or not results.get("ids")
            or not results["ids"]
            or len(results["ids"]) == 0
            or not results["ids"][0]
        ):
            logger.info("CACHE MISS: No valid documents found for this query.")
            return None

        # Check distances structure step by step
        distances = results.get("distances")
        if (
            not distances
            or len(distances) == 0
            or distances[0] is None
            or len(distances[0]) == 0
        ):
            logger.info("CACHE MISS: No valid distances found for this query.")
            return None

        # Check documents structure step by step
        documents = results.get("documents")
        if (
            not documents
            or len(documents) == 0
            or documents[0] is None
            or len(documents[0]) == 0
        ):
            logger.info("CACHE MISS: No valid documents found for this query.")
            return None

        distance = distances[0][0]
        document = documents[0][0]

        # Handle potential None metadata gracefully
        metadatas = results.get("metadatas")
        metadata = None
        if (
            metadatas
            and len(metadatas) > 0
            and metadatas[0] is not None
            and len(metadatas[0]) > 0
        ):
            metadata = metadatas[0][0]

        if distance < config.CACHE_DISTANCE_THRESHOLD:
            cached_key = metadata.get("composite_key", "N/A") if metadata else "N/A"
            logger.warning(
                f"CACHE HIT! Found a similar report for key '{cached_key}' with distance {distance:.4f}."
            )
            return document
        else:
            logger.info(
                f"CACHE MISS. Closest document distance ({distance:.4f}) is above the threshold."
            )
            return None
    except (IndexError, TypeError, KeyError) as e:
        logger.error(
            f"Error while parsing ChromaDB results: {e}. Assuming cache miss.",
            exc_info=True,
        )
        return None


def add_to_cache(composite_key: str, report_json: str):
    """
    Adds a newly generated report to the cache using the composite key.
    """
    if report_collection is None:
        return
    logger.info(f"Attempting to add new report to cache with key: '{composite_key}'")

    embedding = llm_client.generate_embedding(composite_key)
    if not embedding:
        return

    doc_id = hashlib.sha256(composite_key.encode()).hexdigest()
    try:
        report_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[report_json],
            metadatas=[{"composite_key": composite_key}],
        )
        logger.info(f"Successfully added/updated report with ID {doc_id} in the cache.")
    except Exception as e:
        logger.error(
            f"Failed to add document to ChromaDB collection: {e}", exc_info=True
        )
