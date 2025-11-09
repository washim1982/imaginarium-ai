import os
import time
import threading
from typing import Optional, Dict, Any, List
import requests


TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
TOMORROW_BASE_URL = os.getenv("TOMORROW_BASE_URL", "https://api.tomorrow.io/v4")
TOMORROW_UNITS = os.getenv("TOMORROW_UNITS", "metric")  # metric|imperial
WEATHER_GEOCODE_FALLBACK = (os.getenv("WEATHER_GEOCODE_FALLBACK", "true").lower() == "true")
GEOCODE_URL = os.getenv("GEOCODE_URL", "https://geocode.maps.co/search")
OPENMETEO_URL = os.getenv("OPENMETEO_URL", "https://api.open-meteo.com/v1/forecast")
OPENMETEO_GEOCODE_URL = os.getenv("OPENMETEO_GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")


class WeatherError(Exception):
    pass


def _units_labels(units: str) -> Dict[str, str]:
    if units == "imperial":
        return {"temp": "°F", "speed": "mph"}
    return {"temp": "°C", "speed": "km/h"}


# --- Simple in-process TTL cache (per container) ---
_CACHE_TTL = int(os.getenv("WEATHER_CACHE_SECONDS", "180") or 180)
_CACHE: Dict[tuple, tuple] = {}
_CACHE_LOCK = threading.Lock()


def _cache_get(key: tuple):
    if _CACHE_TTL <= 0:
        return None
    now = time.time()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        expiry, value = entry
        if now >= expiry:
            # expired
            try:
                del _CACHE[key]
            except KeyError:
                pass
            return None
        return value


def _cache_set(key: tuple, value):
    if _CACHE_TTL <= 0:
        return
    expiry = time.time() + _CACHE_TTL
    with _CACHE_LOCK:
        _CACHE[key] = (expiry, value)


def realtime(location: str, units: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch current conditions from Tomorrow.io Realtime API.

    Args:
        location: A place name (e.g., "Boston, MA") or "lat,lon".
        units: "metric" or "imperial" (defaults from env).

    Returns a normalized dict with key fields used by the UI/chat.
    """
    if not TOMORROW_API_KEY:
        raise WeatherError("TOMORROW_API_KEY is not configured")
    if not location or not str(location).strip():
        raise WeatherError("Location is required (e.g., 'City, Country' or 'lat,lon')")

    use_units = (units or TOMORROW_UNITS or "metric").lower()
    ck = ("rt", location.strip().lower(), use_units)
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    url = f"{TOMORROW_BASE_URL.rstrip('/')}/weather/realtime"
    params = {"location": location, "units": use_units, "apikey": TOMORROW_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=8)
    except requests.RequestException as exc:
        # Try Open-Meteo fallback via geocode
        fm = _fallback_openmeteo_realtime(location, use_units)
        if fm:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"connection error: {exc}") from exc

    if resp.status_code >= 400:
        # Try geocoding fallback on invalid location errors
        if WEATHER_GEOCODE_FALLBACK and resp.status_code == 400:
            coords = _geocode_to_coords(location)
            if coords:
                params["location"] = f"{coords['lat']},{coords['lon']}"
                try:
                    retry = requests.get(url, params=params, timeout=8)
                except requests.RequestException as exc:
                    # If Tomorrow.io fails after geocoding, fall back to Open-Meteo
                    fm = _fallback_openmeteo_realtime(location, use_units)
                    if fm:
                        return fm
                    raise WeatherError(f"connection error after geocoding: {exc}") from exc
                if retry.status_code < 400:
                    data = retry.json() or {}
                    values = (data.get("data") or {}).get("values") or {}
                    ts = (data.get("data") or {}).get("time")
                    labels = _units_labels(use_units)
                    result = {
                        "location": location,
                        "observed_at": ts,
                        "units": use_units,
                        "temperature": values.get("temperature"),
                        "temperatureApparent": values.get("temperatureApparent"),
                        "humidity": values.get("humidity"),
                        "windSpeed": values.get("windSpeed"),
                        "weatherCode": values.get("weatherCode"),
                        "precipitationIntensity": values.get("rainIntensity") or values.get("precipitationIntensity"),
                        "uvIndex": values.get("uvIndex"),
                        "visibility": values.get("visibility"),
                        "labels": labels,
                        "raw": data,
                        "resolved_location": params["location"],
                        "resolved_label": coords.get("label"),
                    }
                    _cache_set(ck, result)
                    return result
        # If not a 400, or geocoding didn't help, try Open-Meteo as a final fallback
        fm = _fallback_openmeteo_realtime(location, use_units)
        if fm:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"API error: {resp.status_code} {resp.text}")

    data = resp.json() or {}
    values = (data.get("data") or {}).get("values") or {}
    ts = (data.get("data") or {}).get("time")

    labels = _units_labels(use_units)
    result = {
        "location": location,
        "observed_at": ts,
        "units": use_units,
        "temperature": values.get("temperature"),
        "temperatureApparent": values.get("temperatureApparent"),
        "humidity": values.get("humidity"),
        "windSpeed": values.get("windSpeed"),
        "weatherCode": values.get("weatherCode"),
        "precipitationIntensity": values.get("rainIntensity") or values.get("precipitationIntensity"),
        "uvIndex": values.get("uvIndex"),
        "visibility": values.get("visibility"),
        "labels": labels,
        "raw": data,
    }
    _cache_set(ck, result)
    return result


def forecast(location: str, units: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch a simple daily forecast from Tomorrow.io v4.
    Returns a list of day dicts with date, highs/lows and a few key metrics.
    """
    if not TOMORROW_API_KEY:
        raise WeatherError("TOMORROW_API_KEY is not configured")
    if not location or not str(location).strip():
        raise WeatherError("Location is required")

    use_units = (units or TOMORROW_UNITS or "metric").lower()
    ck = ("daily", location.strip().lower(), use_units, int(days))
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    url = f"{TOMORROW_BASE_URL.rstrip('/')}/weather/forecast"
    params = {
        "location": location,
        "units": use_units,
        "timesteps": "1d",
        "apikey": TOMORROW_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=8)
    except requests.RequestException as exc:
        # Fallback
        fm = _fallback_openmeteo_daily(location, use_units, days)
        if fm is not None:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"connection error: {exc}") from exc

    if resp.status_code >= 400:
        # Do not geocode here; the chat path already geocodes for realtime
        fm = _fallback_openmeteo_daily(location, use_units, days)
        if fm is not None:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"API error: {resp.status_code} {resp.text}")

    data = resp.json() or {}
    timelines = data.get("timelines", {})
    daily = timelines.get("daily") or []
    out: List[Dict[str, Any]] = []
    for item in daily[: max(1, int(days))]:
        vals = item.get("values", {})
        out.append(
            {
                "date": item.get("time"),
                "temperatureMax": vals.get("temperatureMax"),
                "temperatureMin": vals.get("temperatureMin"),
                "precipitationProbabilityAvg": vals.get("precipitationProbabilityAvg"),
                "windSpeedAvg": vals.get("windSpeedAvg"),
                "weatherCodeMax": vals.get("weatherCodeMax"),
                "sunriseTime": vals.get("sunriseTime"),
                "sunsetTime": vals.get("sunsetTime"),
                "uvIndexMax": vals.get("uvIndexMax"),
            }
        )
    _cache_set(ck, out)
    return out


def forecast_hourly(location: str, units: Optional[str] = None, hours: int = 12) -> List[Dict[str, Any]]:
    """
    Fetch an hourly forecast for the next `hours` hours (default 12).
    Returns list of { time, temperature, temperatureApparent, precipitationProbability, windSpeed, weatherCode }.
    """
    if not TOMORROW_API_KEY:
        raise WeatherError("TOMORROW_API_KEY is not configured")
    if not location or not str(location).strip():
        raise WeatherError("Location is required")

    use_units = (units or TOMORROW_UNITS or "metric").lower()
    ck = ("hourly", location.strip().lower(), use_units, int(hours))
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    url = f"{TOMORROW_BASE_URL.rstrip('/')}/weather/forecast"
    params = {
        "location": location,
        "units": use_units,
        "timesteps": "1h",
        "apikey": TOMORROW_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=8)
    except requests.RequestException as exc:
        fm = _fallback_openmeteo_hourly(location, use_units, hours)
        if fm is not None:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"connection error: {exc}") from exc

    if resp.status_code >= 400:
        fm = _fallback_openmeteo_hourly(location, use_units, hours)
        if fm is not None:
            _cache_set(ck, fm)
            return fm
        raise WeatherError(f"API error: {resp.status_code} {resp.text}")


def _map_openmeteo_code_to_tomorrow(code: Optional[int]) -> Optional[int]:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return None
    # Map Open‑Meteo WMO codes to rough Tomorrow.io equivalents
    if c in (0, 1):
        return 1000  # Clear
    if c == 2:
        return 1101  # Partly Cloudy
    if c == 3:
        return 1001  # Cloudy/Overcast
    if c in (45, 48):
        return 2000  # Fog
    if c in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return 4001  # Rain
    if c in (71, 73, 75, 77, 85, 86):
        return 5001  # Snow
    if c in (56, 57, 66, 67):
        return 6201  # Sleet/Ice
    if c in (95, 96, 99):
        return 8000  # Thunderstorm
    return None


def _parse_latlon(text: str) -> Optional[Dict[str, str]]:
    import re
    if not text:
        return None
    m = re.search(r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)", str(text))
    if not m:
        return None
    return {"lat": m.group(1), "lon": m.group(2)}


def _coords_for(location: str) -> Optional[Dict[str, str]]:
    return _parse_latlon(location) or _geocode_to_coords(location)


def _fallback_openmeteo_realtime(location: str, units: str) -> Optional[Dict[str, Any]]:
    coords = _coords_for(location)
    if not coords:
        return None
    lat, lon = coords["lat"], coords["lon"]
    temp_unit = "celsius" if units == "metric" else "fahrenheit"
    wind_unit = "kmh" if units == "metric" else "mph"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m", "weather_code", "uv_index", "visibility"],
        "temperature_unit": temp_unit,
        "windspeed_unit": wind_unit,
        "forecast_days": 1,
    }
    try:
        r = requests.get(OPENMETEO_URL, params=params, timeout=8)
        if r.status_code >= 400:
            return None
        j = r.json() or {}
        cur = (j.get("current") or {})
        labels = _units_labels(units)
        return {
            "location": location,
            "observed_at": cur.get("time"),
            "units": units,
            "temperature": cur.get("temperature_2m"),
            "temperatureApparent": cur.get("apparent_temperature"),
            "humidity": cur.get("relative_humidity_2m"),
            "windSpeed": cur.get("wind_speed_10m"),
            "weatherCode": _map_openmeteo_code_to_tomorrow(cur.get("weather_code")),
            "uvIndex": cur.get("uv_index"),
            "visibility": cur.get("visibility"),
            "labels": labels,
            "raw": j,
            "resolved_location": f"{lat},{lon}",
            "resolved_label": coords.get("label"),
        }
    except requests.RequestException:
        return None


def _fallback_openmeteo_daily(location: str, units: str, days: int) -> Optional[List[Dict[str, Any]]]:
    coords = _coords_for(location)
    if not coords:
        return None
    lat, lon = coords["lat"], coords["lon"]
    temp_unit = "celsius" if units == "metric" else "fahrenheit"
    wind_unit = "kmh" if units == "metric" else "mph"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "wind_speed_10m_max",
            "sunrise", "sunset", "uv_index_max"
        ],
        "temperature_unit": temp_unit,
        "windspeed_unit": wind_unit,
        "forecast_days": max(1, int(days)),
    }
    try:
        r = requests.get(OPENMETEO_URL, params=params, timeout=8)
        if r.status_code >= 400:
            return None
        j = r.json() or {}
        times = (j.get("daily") or {}).get("time") or []
        vals = j.get("daily") or {}
        out: List[Dict[str, Any]] = []
        for i, t in enumerate(times):
            out.append({
                "date": t,
                "temperatureMax": (vals.get("temperature_2m_max") or [None])[i],
                "temperatureMin": (vals.get("temperature_2m_min") or [None])[i],
                "precipitationProbabilityAvg": (vals.get("precipitation_probability_max") or [None])[i],
                "windSpeedAvg": (vals.get("wind_speed_10m_max") or [None])[i],
                "weatherCodeMax": _map_openmeteo_code_to_tomorrow((vals.get("weather_code") or [None])[i]),
                "sunriseTime": (vals.get("sunrise") or [None])[i],
                "sunsetTime": (vals.get("sunset") or [None])[i],
                "uvIndexMax": (vals.get("uv_index_max") or [None])[i],
            })
        return out
    except requests.RequestException:
        return None


def _fallback_openmeteo_hourly(location: str, units: str, hours: int) -> Optional[List[Dict[str, Any]]]:
    coords = _coords_for(location)
    if not coords:
        return None
    lat, lon = coords["lat"], coords["lon"]
    temp_unit = "celsius" if units == "metric" else "fahrenheit"
    wind_unit = "kmh" if units == "metric" else "mph"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["weather_code", "temperature_2m", "apparent_temperature", "precipitation_probability", "wind_speed_10m"],
        "temperature_unit": temp_unit,
        "windspeed_unit": wind_unit,
        "forecast_days": 1,
    }
    try:
        r = requests.get(OPENMETEO_URL, params=params, timeout=8)
        if r.status_code >= 400:
            return None
        j = r.json() or {}
        times = (j.get("hourly") or {}).get("time") or []
        vals = j.get("hourly") or {}
        out: List[Dict[str, Any]] = []
        for i, t in enumerate(times[: max(1, int(hours))]):
            out.append({
                "time": t,
                "temperature": (vals.get("temperature_2m") or [None])[i],
                "temperatureApparent": (vals.get("apparent_temperature") or [None])[i],
                "precipitationProbability": (vals.get("precipitation_probability") or [None])[i],
                "windSpeed": (vals.get("wind_speed_10m") or [None])[i],
                "weatherCode": _map_openmeteo_code_to_tomorrow((vals.get("weather_code") or [None])[i]),
            })
        return out
    except requests.RequestException:
        return None

    data = resp.json() or {}
    timelines = data.get("timelines", {})
    hourly = timelines.get("hourly") or []
    out: List[Dict[str, Any]] = []
    for item in hourly[: max(1, int(hours))]:
        vals = item.get("values", {})
        out.append(
            {
                "time": item.get("time"),
                "temperature": vals.get("temperature"),
                "temperatureApparent": vals.get("temperatureApparent"),
                "precipitationProbability": vals.get("precipitationProbability"),
                "windSpeed": vals.get("windSpeed"),
                "weatherCode": vals.get("weatherCode"),
            }
        )
    _cache_set(ck, out)
    return out


def _geocode_to_coords(query: str) -> Optional[Dict[str, str]]:
    """Resolve a place name to lat/lon using a public geocoding service.

    This is a best-effort fallback for misspelled or ambiguous locations.
    Returns a dict {"lat": str, "lon": str} or None on failure.
    """
    q = (query or "").strip()
    if not q:
        return None
    # Normalize common trailing time words so queries like "denver today" resolve
    try:
        import re as _re
        qn = _re.sub(r"\b(?:today|now|tonight|tomorrow|this\s+(?:morning|afternoon|evening|week|weekend))\b\s*$", "", q, flags=_re.IGNORECASE).strip()
        if qn:
            q = qn
    except Exception:
        pass
    # Provider 1: OSM via maps.co
    try:
        resp = requests.get(GEOCODE_URL, params={"q": q, "format": "json", "limit": 1}, timeout=10)
        if resp.status_code < 400:
            arr = resp.json() or []
            if arr:
                first = arr[0]
                lat = first.get("lat")
                lon = first.get("lon")
                if lat and lon:
                    label = first.get("display_name") or first.get("name") or q
                    return {"lat": str(lat), "lon": str(lon), "label": str(label)}
    except requests.RequestException:
        pass

    # Provider 2: Open‑Meteo Geocoding (no key required)
    try:
        resp2 = requests.get(OPENMETEO_GEOCODE_URL, params={"name": q, "count": 1, "language": "en"}, timeout=10)
        if resp2.status_code < 400:
            data = resp2.json() or {}
            results = data.get("results") or []
            if results:
                r = results[0]
                lat = r.get("latitude")
                lon = r.get("longitude")
                if lat is not None and lon is not None:
                    label_parts = [r.get("name"), r.get("admin1"), r.get("country")]
                    label = ", ".join([p for p in label_parts if p]) or q
                    return {"lat": str(lat), "lon": str(lon), "label": str(label)}
    except requests.RequestException:
        pass

    return None
