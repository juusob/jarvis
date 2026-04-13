import asyncio
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from livekit.agents import RunContext, function_tool

logger = logging.getLogger("weather-tool")

FMI_WFS_URL = "https://opendata.fmi.fi/wfs"
STORED_QUERY_ID = "fmi::observations::weather::simple"
PARAMETERS = "temperature,windspeedms,humidity,winddirection,pressure"

# XML namespaces used in FMI responses
NAMESPACES = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "BsWfs": "http://xml.fmi.fi/schema/wfs/2.0",
    "gml": "http://www.opengis.net/gml/3.2",
}


def _build_fmi_url(place: str) -> str:
    return (
        f"{FMI_WFS_URL}?service=WFS&version=2.0.0&request=getFeature"
        f"&storedquery_id={STORED_QUERY_ID}"
        f"&place={quote(place)}"
        f"&parameters={PARAMETERS}"
        f"&timestep=60"
    )


def _parse_fmi_response(xml_text: str) -> dict[str, Any]:
    """Parse FMI simple feature XML response into a dict of latest observations."""
    root = ET.fromstring(xml_text)
    members = root.findall("wfs:member", NAMESPACES)

    if not members:
        return {}

    # Collect all observations, keeping only the latest value per parameter
    observations: dict[str, dict[str, str]] = {}
    latest_time = ""
    location_name = ""

    for member in members:
        element = member.find("BsWfs:BsWfsElement", NAMESPACES)
        if element is None:
            continue

        time_el = element.find("BsWfs:Time", NAMESPACES)
        param_name_el = element.find("BsWfs:ParameterName", NAMESPACES)
        param_value_el = element.find("BsWfs:ParameterValue", NAMESPACES)

        if time_el is None or param_name_el is None or param_value_el is None:
            continue

        time_str = time_el.text or ""
        param_name = param_name_el.text or ""
        param_value = (param_value_el.text or "").strip()

        if not location_name:
            loc_el = element.find("BsWfs:Location", NAMESPACES)
            if loc_el is not None:
                point = loc_el.find("gml:Point", NAMESPACES)
                if point is not None:
                    name_el = point.find("gml:name", NAMESPACES)
                    if name_el is not None and name_el.text:
                        location_name = name_el.text

        if time_str >= latest_time:
            latest_time = time_str
            observations[param_name] = {
                "value": param_value,
                "time": time_str,
            }

    if not observations:
        return {}

    result: dict[str, Any] = {"observation_time": latest_time}
    if location_name:
        result["location"] = location_name

    param_labels = {
        "temperature": ("temperature_celsius", "°C"),
        "windspeedms": ("wind_speed_ms", "m/s"),
        "humidity": ("humidity_percent", "%"),
        "winddirection": ("wind_direction_degrees", "°"),
        "pressure": ("pressure_hpa", "hPa"),
    }

    for param_name, obs in observations.items():
        value = obs["value"]
        if value == "NaN":
            continue
        label, unit = param_labels.get(param_name, (param_name, ""))
        try:
            result[label] = f"{float(value):.1f} {unit}".strip()
        except ValueError:
            result[label] = f"{value} {unit}".strip()

    return result


def _fetch_weather(place: str) -> str:
    """Synchronous fetch and parse of FMI weather data."""
    url = _build_fmi_url(place)
    req = urllib.request.Request(url, headers={"Accept": "application/xml"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode("utf-8")


@function_tool()
async def lookup_weather(
    context: RunContext,
    location: str,
) -> dict[str, Any] | str:
    """Look up current weather observations in Finland from the Finnish Meteorological Institute (FMI).

    This tool provides real-time weather data for locations in Finland, including
    temperature, wind speed, humidity, wind direction, and air pressure.
    Only Finnish locations are supported. If the location is not found or not in
    Finland, the tool will indicate this.

    Args:
        location: The Finnish city or place name to look up weather for (e.g. Helsinki, Tampere, Oulu, Rovaniemi).
    """
    logger.info(f"Looking up FMI weather for {location}")

    try:
        xml_text = await asyncio.to_thread(_fetch_weather, location)
    except HTTPError as e:
        if e.code == 400:
            return f"Location '{location}' was not found. Please provide a valid Finnish city or place name."
        return f"FMI weather service returned an error (HTTP {e.code}). Please try again later."
    except (URLError, TimeoutError):
        return "Unable to reach the FMI weather service. Please try again later."

    result = _parse_fmi_response(xml_text)
    if not result:
        return f"No weather observations found for '{location}'. Please check the location name is a valid Finnish city or place."

    return result
