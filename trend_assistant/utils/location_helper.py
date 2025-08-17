"""
Enhanced utility for determining the user's geographical location.
Features multiple API fallbacks, better error handling, and caching.
"""

import requests
import json
import time
from typing import Optional, Dict, Any
from .logger import logger

# Multiple geolocation APIs for redundancy
GEOLOCATION_APIS = [
    {
        "name": "ip-api.com",
        "url": "https://ip-api.com/json",
        "timeout": 5,
        "parser": "_parse_ipapi_response",
        "rate_limit": 15,  # requests per minute
    },
    {
        "name": "ipapi.co",
        "url": "https://ipapi.co/json/",
        "timeout": 5,
        "parser": "_parse_ipapico_response",
        "rate_limit": 30,  # requests per minute for free tier
    },
    {
        "name": "httpbin.org",
        "url": "https://httpbin.org/ip",
        "timeout": 3,
        "parser": "_parse_httpbin_response",
        "rate_limit": 100,  # More permissive
        "ip_only": True,  # Only returns IP, would need secondary lookup
    },
    {
        "name": "ipinfo.io",
        "url": "https://ipinfo.io/json",
        "timeout": 5,
        "parser": "_parse_ipinfo_response",
        "rate_limit": 50,  # requests per day for free tier
    },
]

# Simple cache to avoid repeated requests
_location_cache = {"location": None, "timestamp": None, "ttl": 3600}  # 1 hour TTL


def _parse_ipapi_response(data: Dict[Any, Any]) -> Optional[str]:
    """Parse ip-api.com response."""
    if data.get("status") == "success":
        city = data.get("city")
        country = data.get("country")
        if city and country:
            return f"{city}, {country}"
    return None


def _parse_ipapico_response(data: Dict[Any, Any]) -> Optional[str]:
    """Parse ipapi.co response."""
    city = data.get("city")
    country_name = data.get("country_name")
    if city and country_name:
        return f"{city}, {country_name}"
    return None


def _parse_ipinfo_response(data: Dict[Any, Any]) -> Optional[str]:
    """Parse ipinfo.io response."""
    city = data.get("city")
    country = data.get("country")
    if city and country:
        # ipinfo.io returns country codes, might want to expand this
        return f"{city}, {country}"
    return None


def _parse_httpbin_response(data: Dict[Any, Any]) -> Optional[str]:
    """Parse httpbin.org response (IP only)."""
    # This would only give us IP, not location
    # Could be used for secondary lookup if needed
    return None


def _is_cache_valid() -> bool:
    """Check if cached location is still valid."""
    if not _location_cache["location"] or not _location_cache["timestamp"]:
        return False

    elapsed = time.time() - _location_cache["timestamp"]
    return elapsed < _location_cache["ttl"]


def _cache_location(location: str) -> None:
    """Cache the location result."""
    _location_cache["location"] = location
    _location_cache["timestamp"] = time.time()


def _try_geolocation_api(api_config: Dict[str, Any]) -> Optional[str]:
    """
    Try a single geolocation API.

    Args:
        api_config: API configuration dictionary

    Returns:
        Location string if successful, None otherwise
    """
    try:
        logger.debug(f"Trying geolocation API: {api_config['name']}")

        # Make request with specified timeout
        response = requests.get(
            api_config["url"],
            timeout=api_config["timeout"],
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        response.raise_for_status()

        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {api_config['name']}: {e}")
            return None

        # Use the appropriate parser
        parser_name = api_config["parser"]
        if parser_name == "_parse_ipapi_response":
            return _parse_ipapi_response(data)
        elif parser_name == "_parse_ipapico_response":
            return _parse_ipapico_response(data)
        elif parser_name == "_parse_ipinfo_response":
            return _parse_ipinfo_response(data)
        elif parser_name == "_parse_httpbin_response":
            return _parse_httpbin_response(data)

        return None

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred for {api_config['name']}")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning(f"Rate limit exceeded for {api_config['name']}")
        else:
            logger.warning(
                f"HTTP error {e.response.status_code} for {api_config['name']}"
            )
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error for {api_config['name']}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error for {api_config['name']}: {e}")
        return None


def get_location_from_ip() -> Optional[str]:
    """
    Determines the user's location based on their public IP address.

    Uses multiple geolocation APIs as fallbacks and implements caching
    to reduce API calls.

    Returns:
        A formatted location string (e.g., "London, United Kingdom") on success,
        or None if the location cannot be determined.
    """
    logger.info("Attempting to determine user location from public IP...")

    # Check cache first
    if _is_cache_valid():
        logger.info(f"Using cached location: {_location_cache['location']}")
        return _location_cache["location"]

    # Try each API in order until one succeeds
    for api_config in GEOLOCATION_APIS:
        # Skip IP-only APIs for now (would need secondary lookup)
        if api_config.get("ip_only", False):
            continue

        location = _try_geolocation_api(api_config)
        if location:
            logger.info(
                f"Successfully determined location using {api_config['name']}: {location}"
            )
            _cache_location(location)
            return location
        else:
            logger.debug(f"Failed to get location from {api_config['name']}")

    logger.warning("All geolocation APIs failed to determine location")
    return None


def get_location_with_fallback(fallback_location: str = "Global") -> str:
    """
    Get location with a guaranteed fallback.

    Args:
        fallback_location: Default location to use if detection fails

    Returns:
        Either the detected location or the fallback location
    """
    detected_location = get_location_from_ip()
    if detected_location:
        return detected_location

    logger.info(f"Using fallback location: {fallback_location}")
    return fallback_location


def test_all_apis() -> Dict[str, Any]:
    """
    Test all configured geolocation APIs and return results.
    Useful for debugging and monitoring API availability.

    Returns:
        Dictionary with test results for each API
    """
    logger.info("Testing all geolocation APIs...")
    results = {}

    for api_config in GEOLOCATION_APIS:
        if api_config.get("ip_only", False):
            results[api_config["name"]] = {"status": "skipped", "reason": "IP-only API"}
            continue

        start_time = time.time()
        location = _try_geolocation_api(api_config)
        response_time = time.time() - start_time

        results[api_config["name"]] = {
            "status": "success" if location else "failed",
            "location": location,
            "response_time": round(response_time, 2),
            "rate_limit": api_config.get("rate_limit", "unknown"),
        }

    # Log summary
    successful_apis = [
        name for name, result in results.items() if result["status"] == "success"
    ]
    logger.info(
        f"API test completed. {len(successful_apis)} out of {len(results)} APIs successful"
    )

    return results


# Backward compatibility with your existing code
def get_location_from_ip_legacy() -> Optional[str]:
    """Legacy version matching your original implementation."""
    IP_GEOLOCATION_API_URL = "https://ip-api.com/json"

    logger.info("Attempting to determine user location from public IP (legacy)...")
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
