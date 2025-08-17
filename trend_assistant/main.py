"""
Main entry point for the Fashion Trend Assistant application.
(Definitive version with a clean Natural Language Interface)
"""

import asyncio
import time
from .services import workflow_service
from .utils.logger import logger
from .utils import brief_utils

# --- USER INTERFACE: The Natural Language Brief -----------------------------
# This is the single point of interaction for the user.
# Simply write your creative idea in the multi-line string below.

USER_PASSAGE = """
I need trend inspiration for luxury menswear in Dubai. Think sharp tailoring with a modern twist, fabrics suitable for hot climates, but still sophisticated.
"""

# --- Main Application Logic --------------------------------------------------


async def main():
    """The main asynchronous function that orchestrates the application run."""
    logger.info("=========================================================")
    logger.info("    FASHION TREND ASSISTANT - CREATIVE PROCESS STARTED   ")
    logger.info("=========================================================")

    start_time = time.time()

    # --- NEW: Phase 0 - AI-Powered Brief Deconstruction ---
    structured_brief = brief_utils.deconstruct_brief_with_ai(USER_PASSAGE)

    if not structured_brief:
        logger.critical(
            "Could not understand the creative brief. Please rephrase your request."
        )
        return

    try:
        # The deconstructed brief is then passed into our workflow.
        # The service layer is now responsible for all validation and defaults.
        await workflow_service.run_creative_process(
            season=structured_brief.get("season"),
            year=structured_brief.get("year"),
            theme_hint=structured_brief.get("theme_hint"),
            target_audience=structured_brief.get("target_audience"),
            region=structured_brief.get("region"),
        )
    except Exception as e:
        logger.critical(f"A critical unexpected error occurred: {e}", exc_info=True)
    finally:
        duration = time.time() - start_time
        logger.info("=========================================================")
        logger.info(f"    CREATIVE PROCESS FINISHED in {duration:.2f} seconds")
        logger.info("=========================================================")


if __name__ == "__main__":
    asyncio.run(main())
