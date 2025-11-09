from fastapi import APIRouter, HTTPException, Query

from app.services.weather_service import WeatherError, realtime, forecast, forecast_hourly


router = APIRouter(prefix="/api", tags=["Weather"])


@router.get("/weather")
def get_weather(
    location: str = Query(..., description="City name or 'lat,lon'"),
    units: str | None = Query(None),
):
    try:
        current = realtime(location, units)
        loc_for_forecast = current.get("resolved_location") or location
        daily = forecast(loc_for_forecast, units)
        hourly = forecast_hourly(loc_for_forecast, units, hours=12)
        return {"weather": {"current": current, "daily": daily, "hourly": hourly}}
    except WeatherError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
