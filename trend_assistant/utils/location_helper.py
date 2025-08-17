"""
Utility for determining the user's geographical location.
"""

import requests
from typing import Optional
from .logger import logger

# --- CORRECTED: Using the secure HTTPS endpoint ---
IP_GEOLOCATION_API_URL = "https://ip-api.com/json"


def get_location_from_ip() -> Optional[str]:
    """
    Determines the user's location based on their public IP address.

    Makes a request to a secure geolocation API and parses the response to get
    a 'City, Country' string.

    Returns:
        A formatted location string (e.g., "London, United Kingdom") on success,
        or None if the location cannot be determined.
    """
    logger.info("Attempting to determine user location from public IP...")
    try:
        response = requests.get(IP_GEOLOCATION_API_URL, timeout=5)
        response.raise_for_status()

        data = response.json()

        if data.get("status") == "success":
            city = data.get("city")
            country = data.get("country")
            if city and country:
                location_string = f"{city}, {country}"
                logger.info(f"Successfully determined location: {location_string}")
                return location_string

        logger.warning(
            f"Geolocation API returned a non-success status: {data.get('message')}"
        )
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"A network error occurred during location lookup: {e}")
        return None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during location lookup: {e}", exc_info=True
        )
        return None
