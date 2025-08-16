"""
Main entry point for the Fashion Trend Assistant application.
"""

import asyncio
import time

# --- MODIFIED IMPORTS ---
from .services import workflow_service
from .utils.logger import logger
from .utils.location_helper import get_location_from_ip  # Import our new function

# --- Creative Brief Configuration --------------------------------------------

# --- Tier 1: Core Creative Idea (Required) ---
SEASON = "Spring/Summer"
YEAR = 2025
THEME_HINT = "Contemporary Pahela Baishakh wear blending Jamdani with modern cuts"
TARGET_AUDIENCE = "Urban millennials and cultural enthusiasts (20-35)"

# --- Tier 2: Location (Dynamic with Manual Override) ---
# The system will try to detect your location automatically.
# If you want to override it, simply type a location into the REGION variable.
# Default is None, which means it will try to detect automatically.
# Example: REGION = "Paris, France"
REGION_OVERRIDE = "Dhaka, Bangladesh"

# --- Main Application Logic --------------------------------------------------


async def main():
    """The main asynchronous function that orchestrates the application run."""
    logger.info("=========================================================")
    logger.info("    FASHION TREND ASSISTANT - CREATIVE PROCESS STARTED   ")
    logger.info("=========================================================")

    # --- DYNAMIC REGION LOGIC ---
    # Determine the final region to use for the creative brief.
    # If the user has provided a manual override, use it.
    if REGION_OVERRIDE:
        final_region = REGION_OVERRIDE
        logger.info(f"Using manually specified region: {final_region}")
    else:
        # Otherwise, attempt to detect the location automatically.
        final_region = get_location_from_ip()
        if not final_region:
            logger.warning(
                "Could not determine location automatically. Proceeding with a broader, non-regional search."
            )

    start_time = time.time()
    try:
        await workflow_service.run_creative_process(
            season=SEASON,
            year=YEAR,
            theme_hint=THEME_HINT,
            target_audience=TARGET_AUDIENCE,
            region=final_region,  # Pass the final, determined region to the service
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
