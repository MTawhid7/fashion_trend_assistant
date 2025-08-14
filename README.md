# Fashion Trend Assistant

## Overview

The Fashion Trend Assistant is an advanced AI-powered command-line application that automates the entire fashion trend research and concept development process. It leverages Google's Gemini API and a sophisticated web scraping engine to synthesize real-world data into actionable creative reports for fashion designers and enthusiasts.

The system performs a multi-stage workflow:
1.  **Intelligence Gathering:** Performs targeted Google searches on authoritative fashion sources (like Vogue, WGSN, etc.).
2.  **Surgical Scraping:** Uses Playwright to intelligently scrape and extract the main article content from each source.
3.  **Intelligent Summarization:** Employs the Gemini API to distill each scraped document into a concise, relevant summary, respecting API rate limits with a robust batching system.
4.  **Data Synthesis:** Analyzes the collection of summaries to generate a single, cohesive, and structured JSON trend report, complete with themes, cultural drivers, key garments, fabrics, and color palettes.
5.  **Prompt Generation:** Creates a final JSON file containing professionally art-directed prompts (for inspiration boards, mood boards, and final garments) ready to be used in AI image generation models like Midjourney or DALL-E 3.

## Features

-   **Automated Research:** Dynamically generates and executes search queries.
-   **Intelligent Content Extraction:** Focuses on primary article content to improve data quality.
-   **AI-Powered Summarization:** Distills large amounts of text into dense, relevant insights.
-   **Rate Limit Handling:** Uses an asynchronous batching system to manage API calls efficiently.
-   **Structured Data Output:** Generates a validated JSON report based on Pydantic models.
-   **Creative Prompt Engineering:** Produces high-quality, art-directed prompts for visual concept creation.
-   **Comprehensive Logging:** Logs the entire workflow to `logs/app.log` for easy monitoring and debugging.

## Setup and Installation

### Prerequisites

-   Python 3.10+
-   Access to the Google Gemini API and a Google Custom Search Engine.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/fashion_trend_assistant.git
cd fashion_trend_assistant
```

### 2. Create and Activate a Virtual Environment

```bash
# Create the virtual environment
python -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Or activate it (Windows)
# venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

Playwright requires a separate step to download the headless browser binaries.

```bash
playwright install
```

### 5. Configure Environment Variables

Create a `.env` file in the root of the project by copying the example:

```bash
cp .env.example .env
```

Now, open the `.env` file and add your secret API keys:

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
GOOGLE_API_KEY="YOUR_GOOGLE_CLOUD_API_KEY_HERE"
SEARCH_ENGINE_ID="YOUR_SEARCH_ENGINE_ID_HERE"
```

## How to Run

The creative brief (season, year, theme) is configured directly in the main script.

1.  Open `trend_assistant/main.py`.
2.  Modify the `SEASON`, `YEAR`, and `THEME_HINT` variables to define your concept.
3.  Run the application from the root directory:

```bash
python -m trend_assistant.main
```

The process will take several minutes to complete. The final output files will be saved in the `/results` directory.