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
    Return the current time for a given city name or timezone identifier.
    
    Parameters:
        city (str): City name or timezone identifier (e.g., "Tokyo", "Asia/Tokyo", "America/New_York").
    
    Returns:
        dict: On success, a dictionary with:
            - status: "success"
            - city: the input `city`
            - time: formatted local time as "YYYY-MM-DD HH:MM:SS TZ±HHMM" (e.g., "2025-10-27 15:30:45 JST+0900")
            - timezone: string representation of the resolved timezone (e.g., "Asia/Tokyo")
            - iso_format: ISO 8601 representation of the current time
          On error, a dictionary with:
            - status: "error"
            - city: the input `city`
            - error_message: a human-readable explanation of the failure (may suggest valid timezone identifiers)
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