"""
Main entry point for the Fashion Trend Assistant application.

This script initializes the application and starts the creative workflow.
To run the assistant, execute this file from the command line:
`python -m trend_assistant.main`
"""

import asyncio
import time

# Import the main service function and the logger
from .services import workflow_service
from .utils.logger import logger

# --- Creative Brief Configuration --------------------------------------------
# This is the main control panel for the user.
# Define the high-level creative direction for the desired trend report.

SEASON = "Fall/Winter"
YEAR = 2025
THEME_HINT = "Quiet luxury meets utilitarian workwear"


# --- Main Application Logic --------------------------------------------------


async def main():
    """
    The main asynchronous function that orchestrates the application run.
    """
    logger.info("=========================================================")
    logger.info("    FASHION TREND ASSISTANT - CREATIVE PROCESS STARTED   ")
    logger.info("=========================================================")

    start_time = time.time()

    try:
        # Call the main service function with the defined creative brief.
        # This single call will trigger the entire four-phase workflow.
        await workflow_service.run_creative_process(
            season=SEASON, year=YEAR, theme_hint=THEME_HINT
        )
    except Exception as e:
        # A top-level exception handler to catch any unexpected critical errors
        # that might not have been caught in the lower-level modules.
        logger.critical(
            f"A critical unexpected error occurred at the top level: {e}", exc_info=True
        )
    finally:
        end_time = time.time()
        duration = end_time - start_time
        logger.info("=========================================================")
        logger.info(f"    CREATIVE PROCESS FINISHED in {duration:.2f} seconds")
        logger.info("=========================================================")


# --- Script Execution --------------------------------------------------------

if __name__ == "__main__":
    # This block allows the script to be run directly.
    # `asyncio.run()` starts the asynchronous event loop.
    asyncio.run(main())
