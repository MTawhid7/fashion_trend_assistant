"""
Utility for determining the user's geographical location.
"""

import requests
from typing import Optional
from .logger import logger

# We will use a free, simple, and reliable IP geolocation API.
IP_GEOLOCATION_API_URL = "http://ip-api.com/json"


def get_location_from_ip() -> Optional[str]:
    """
    Determines the user's location based on their public IP address.

    Makes a request to a geolocation API and parses the response to get
    a 'City, Country' string.

    Returns:
        A formatted location string (e.g., "London, United Kingdom") on success,
        or None if the location cannot be determined.
    """
    logger.info("Attempting to determine user location from public IP...")
    try:
        # Make the request with a reasonable timeout.
        response = requests.get(IP_GEOLOCATION_API_URL, timeout=5)
        # Raise an exception if the request was not successful (e.g., 4xx or 5xx error).
        response.raise_for_status()

        data = response.json()

        # The API returns 'success' in the status field on a good lookup.
        if data.get("status") == "success":
            city = data.get("city")
            country = data.get("country")
            if city and country:
                location_string = f"{city}, {country}"
                logger.info(f"Successfully determined location: {location_string}")
                return location_string

        # If status is not 'success' or data is missing, log it.
        logger.warning(
            f"Geolocation API returned a non-success status: {data.get('message')}"
        )
        return None

    except requests.exceptions.RequestException as e:
        # This catches network errors, timeouts, etc.
        logger.error(f"A network error occurred during location lookup: {e}")
        return None
    except Exception as e:
        # This catches other potential errors, like JSON decoding.
        logger.error(
            f"An unexpected error occurred during location lookup: {e}", exc_info=True
        )
        return None
