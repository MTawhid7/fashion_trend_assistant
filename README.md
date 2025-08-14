# Fashion Trend Assistant

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

An AI-powered engine for automated fashion trend research, analysis, and creative concept development. This tool transforms a simple creative hint into a detailed, structured design brief and a complete set of art-directed prompts for visual creation.

## Core Features

-   **🧠 Semantic Caching:** Blazing-fast results (<2 seconds) for similar creative briefs. Powered by a persistent ChromaDB vector database, it finds conceptually related past reports, saving significant time and API costs.
-   **🤖 Intelligent Summarization:** Employs a multi-stage AI workflow. Instead of analyzing raw data, it first uses Gemini to distill dozens of scraped articles into dense, relevant summaries.
-   **🎯 Surgical Content Extraction:** Uses Playwright and BeautifulSoup to intelligently identify and scrape primary article content, filtering out irrelevant noise like ads, navigation, and footers for higher-quality data.
-   **🛡️ Robust & Resilient:** Built with modern asynchronous programming (`asyncio`), it handles network errors gracefully and uses a sophisticated batching system to manage API rate limits without crashing.
-   **📝 Structured & Validated Output:** Generates a detailed JSON trend report that is rigorously validated against Pydantic models, ensuring data integrity and predictability.
-   **🎨 Creative Prompt Generation:** Produces a final JSON file containing professionally art-directed prompts for generating inspiration boards, mood boards, and final garment concepts in AI image models.

## How It Works: Architectural Overview

The application follows a sophisticated, multi-stage intelligence pipeline that mimics an expert human research workflow:

```
[ User Input: Theme, Season, Year, etc. ]
              |
              v
[ 1. Cache Service: Semantic Check ] --(Cache Hit)--> [ 5. Prompt Generation ]
              |
              | (Cache Miss)
              v
[ 2. Research Client: Scrape Documents ]
              |
              v
[ 3. LLM Client: Summarize Documents (in Batches) ]
              |
              v
[ 4. LLM Client: Synthesize Summaries into Final Report ]
              |
              +--> [ Cache Service: Add New Report to Cache ]
              |
              v
[ 5. Prompt Generation: Create Image Prompts ]
              |
              v
[ Final Output: Two JSON files in /results ]
```

## Tech Stack

-   **Core Language:** Python 3.10+
-   **AI & Language Models:** Google Gemini API (`google-genai` SDK)
-   **Vector Database / Caching:** ChromaDB
-   **Web Scraping & Automation:** Playwright & BeautifulSoup
-   **Data Validation:** Pydantic
-   **API & Search:** Google Custom Search API
-   **Asynchronous Programming:** `asyncio`

## Setup and Installation

### Prerequisites

-   Python 3.10 or newer.
-   An active Google Gemini API Key.
-   A configured Google Cloud Project with the Custom Search API enabled and an API Key / Search Engine ID.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/fashion_trend_assistant.git
cd fashion_trend_assistant
```

### 2. Create and Activate a Virtual Environment

```bash
# Create the virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

Playwright requires a separate one-time step to download the headless browser binaries it uses for scraping.

```bash
playwright install
```

### 5. Configure Secrets

The project uses a `.env` file to manage secret API keys. A template is provided.

```bash
# Create your personal .env file from the example
cp .env.example .env
```

Now, open the newly created `.env` file and add your secret keys.

## Usage

The creative brief for the trend report is configured directly in the main script.

1.  Open `trend_assistant/main.py`.
2.  Modify the `SEASON`, `YEAR`, and `THEME_HINT` variables. You can also provide optional `TARGET_AUDIENCE` and `REGION` for more specific results.
3.  Run the application from the project's **root directory**:

```bash
python -m trend_assistant.main
```

The process will run for several minutes on a "cache miss" and less than two seconds on a "cache hit." The final output files will be saved in the `/results` directory.

## Understanding the Output

The application generates two key files in the `/results` folder:

1.  **`itemized_fashion_trends.json`**: This is the "brain" of the creative concept. It's a highly structured report containing the overarching theme, cultural drivers, and a detailed breakdown of key clothing pieces with their fabrics, colors, silhouettes, and more.
2.  **`generated_prompts.json`**: This is the "art director's shot list." It contains ready-to-use, detailed prompts for each key piece, designed to be copied into AI image generation tools (like Midjourney or DALL-E 3) to create visual representations of the concept.

## Project Roadmap

-   [ ] **Tier 1:** Implement a full Command-Line Interface (CLI) using `Typer` or `argparse`.
-   [ ] **Tier 1:** Add a feature to generate a human-readable Markdown (`.md`) report from the final JSON.
-   [ ] **Tier 2:** Integrate an image generation API to automatically create and save the visual assets.
-   [ ] **Tier 3:** Evolve the project into a full web application with a FastAPI backend and a user interface.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.