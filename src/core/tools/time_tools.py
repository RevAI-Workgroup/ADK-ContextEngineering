"""
Time and date tools for getting current time in different timezones.

Based on the proven working example from:
https://github.com/jageenshukla/adk-ollama-tool
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict


def get_current_time(city: str) -> Dict[str, Any]:
    """
    Get the current time in a specified city or timezone.

    Supports both city names (e.g., "Tokyo") and timezone identifiers
    (e.g., "Asia/Tokyo", "America/New_York").

    Args:
        city: City name or timezone identifier (e.g., "Tokyo", "Asia/Tokyo", "America/New_York")

    Returns:
        dict: Current time information with status

    Examples:
        >>> get_current_time("Tokyo")
        {
            "status": "success",
            "city": "Tokyo",
            "time": "2025-10-27 15:30:45 JST+0900",
            "timezone": "Asia/Tokyo"
        }

        >>> get_current_time("America/New_York")
        {
            "status": "success",
            "city": "America/New_York",
            "time": "2025-10-27 02:30:45 EDT-0400",
            "timezone": "America/New_York"
        }
    """
    try:
        # Try to create timezone - this will raise an exception if invalid
        tz_identifier = ZoneInfo(city)

        # Get current time in that timezone
        now = datetime.now(tz_identifier)

        # Format the time string
        time_string = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        return {
            "status": "success",
            "city": city,
            "time": time_string,
            "timezone": str(tz_identifier),
            "iso_format": now.isoformat(),
        }

    except Exception as e:
        # Try to provide a helpful error message
        error_msg = f"Failed to retrieve timezone information for '{city}'. "

        if "No time zone found" in str(e):
            error_msg += (
                "Please use a valid timezone identifier like 'Asia/Tokyo', "
                "'America/New_York', 'Europe/London', etc. "
                "Or try the full timezone path instead of just the city name."
            )
        else:
            error_msg += f"Error: {str(e)}"

        return {
            "status": "error",
            "city": city,
            "error_message": error_msg,
        }
