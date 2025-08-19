"""
Centralized configuration management for the Fashion Trend Assistant.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# --- Path Configuration ---
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_cache"

# --- API Keys & Secrets ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Error: GEMINI_API_KEY is not set.")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY is not set.")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
if not SEARCH_ENGINE_ID:
    raise ValueError("Error: SEARCH_ENGINE_ID is not set.")

# --- LLM & Search Configuration ---
GEMINI_MODEL_NAME = "gemini-2.5-flash"
# --- MODIFIED: Focus on higher quality results ---
SEARCH_NUM_RESULTS = 2

# --- Embedding & Caching Configuration ---
EMBEDDING_MODEL_NAME = "gemini-embedding-001"
CHROMA_COLLECTION_NAME = "fashion_reports"
CACHE_DISTANCE_THRESHOLD = 0.2

# --- Concurrency Configuration ---
GEMINI_API_CONCURRENCY_LIMIT = 5

# --- File & Logging Configuration ---
LOG_FILE_PATH = LOGS_DIR / "app.log"
TREND_REPORT_FILENAME = "itemized_fashion_trends.json"
PROMPTS_FILENAME = "generated_prompts.json"
