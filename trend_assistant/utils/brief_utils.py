"""
Utility functions for handling and preparing the creative brief.
"""

from datetime import datetime
from typing import List, Optional

from .. import config
from ..utils.logger import logger


def prepare_creative_brief(
    season: Optional[str],
    year: Optional[int],
    theme_hint: Optional[str],
    target_audience: Optional[str],
    region: Optional[str],
) -> Optional[dict]:
    """Validates the core inputs and sets smart defaults."""
    if not theme_hint or not theme_hint.strip():
        logger.critical("Halting process: 'THEME_HINT' cannot be empty.")
        return None

    if not season:
        current_month = datetime.now().month
        season = "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
        logger.warning(f"No SEASON provided. Defaulting to current season: '{season}'")

    if not year:
        year = datetime.now().year
        logger.warning(f"No YEAR provided. Defaulting to current year: {year}")

    return {
        "season": season,
        "year": year,
        "theme_hint": theme_hint,
        "target_audience": target_audience,
        "region": region,
    }


def generate_search_queries(brief: dict) -> List[str]:
    """Creates a definitive, multi-tiered list of search queries from the brief."""
    logger.info(
        "Generating a definitive, consolidated set of professional search queries..."
    )

    season, year, theme_hint = brief["season"], brief["year"], brief["theme_hint"]
    target_audience, region = brief["target_audience"], brief["region"]

    audience_query = f" for {target_audience}" if target_audience else ""
    region_search_query = f" in {region}" if region else ""

    tier1_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR trend report OR collection review OR runway analysis) "
        f"(Vogue OR WWD OR Business of Fashion OR Elle){region_search_query}"
    )
    tier2_query = (
        f"({season} {year} OR SS{str(year)[-2:]} OR FW{str(year)[-2:]}) "
        f"({theme_hint} OR key trends OR forecast OR color OR fabric) "
        f"(WGSN OR Trendstop OR Pantone OR Première Vision)"
    )
    tier3_query1 = f"({theme_hint} OR key pieces OR must-have items) {season} {year}{region_search_query}"
    tier3_query2 = (
        f"latest street style {theme_hint}{region_search_query}{audience_query}"
    )
    tier4_query1 = (
        f"'{theme_hint}' aesthetic in contemporary art and fashion{region_search_query}"
    )
    tier4_query2 = f"'{theme_hint}' film and cinema costume style analysis"
    tier4_query3 = f"top fashion bloggers and street style stars in {region}"
    tier4_query4 = f"emerging fashion designers to watch in {region} {year}"

    queries = [
        tier1_query,
        tier2_query,
        tier3_query1,
        tier3_query2,
        tier4_query1,
        tier4_query2,
    ]
    if region:
        queries.extend([tier4_query3, tier4_query4])

    logger.info(f"Generated {len(queries)} definitive, high-quality queries.")
    return queries
