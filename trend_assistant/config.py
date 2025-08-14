"""
Centralized configuration management for the Fashion Trend Assistant.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --- Path Configuration ------------------------------------------------------
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"

# --- API Keys & Secrets ------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Error: GEMINI_API_KEY is not set in the .env file.")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY is not set in the .env file.")

SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
if not SEARCH_ENGINE_ID:
    raise ValueError("Error: SEARCH_ENGINE_ID is not set in the .env file.")

# --- LLM & Search Configuration ----------------------------------------------
GEMINI_MODEL_NAME = "gemini-2.5-flash"
SEARCH_NUM_RESULTS = 5

# --- Concurrency Configuration -----------------------------------------------
# NEW: Controls how many concurrent summarization requests we send to the Gemini API.
# The free tier limit is 10 RPM, so 5 is a safe and efficient value.
GEMINI_API_CONCURRENCY_LIMIT = 5

# --- File & Logging Configuration --------------------------------------------
LOG_FILE_PATH = LOGS_DIR / "app.log"
TREND_REPORT_FILENAME = "itemized_fashion_trends.json"
PROMPTS_FILENAME = "generated_prompts.json"
