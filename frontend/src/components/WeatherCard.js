import React from "react";
import {
  WiDaySunny,
  WiDayCloudy,
  WiCloud,
  WiCloudy,
  WiFog,
  WiRain,
  WiSnow,
  WiSleet,
  WiThunderstorm,
  WiSunrise,
  WiSunset,
} from "react-icons/wi";

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  } catch {
    return iso || "";
  }
}

export default function WeatherCard({ data }) {
  if (!data) return null;
  const current = data.current || {};
  const daily = data.daily || [];
  const hourly = data.hourly || [];
  const labels = (current.labels) || { temp: "°C", speed: "km/h" };
  const distUnit = labels.speed === "mph" ? "mi" : "km";

  const codeToInfo = (code) => {
    const c = Number(code);
    if (Number.isNaN(c)) return { label: "—", Icon: WiCloud };
    // Tomorrow.io weatherCode mapping (grouped)
    if (c === 1000 || c === 1100) return { label: c === 1000 ? "Clear" : "Mostly Clear", Icon: WiDaySunny };
    if (c === 1101) return { label: "Partly Cloudy", Icon: WiDayCloudy };
    if (c === 1102) return { label: "Mostly Cloudy", Icon: WiCloudy };
    if (c === 1001) return { label: "Cloudy", Icon: WiCloud };
    if (c === 2000 || c === 2100) return { label: "Fog", Icon: WiFog };
    if ([4000, 4001, 4200, 4201].includes(c)) return { label: "Rain", Icon: WiRain };
    if ([5000, 5001, 5100, 5101].includes(c)) return { label: "Snow", Icon: WiSnow };
    if ([6000, 6001, 6200, 6201, 7000, 7101, 7102].includes(c)) return { label: "Sleet / Ice", Icon: WiSleet };
    if (c === 8000) return { label: "Thunderstorm", Icon: WiThunderstorm };
    return { label: "—", Icon: WiCloud };
  };

  const curInfo = codeToInfo(current.weatherCode);

  return (
    <div className="weather-card">
      <div className="weather-header">
        <div className="weather-location" title={(current.resolved_label || current.location) || "Weather"}>
          {current.resolved_label || current.location || "Weather"}
          {current.observed_at ? (
            <span className="weather-time"> · {new Date(current.observed_at).toLocaleString()}</span>
          ) : null}
        </div>
        <div className="weather-now">
          <span className="temp">
            {current.temperature != null ? Math.round(current.temperature) : "--"}{labels.temp}
          </span>
          <div className="now-right">
            <div className="summary" title={curInfo.label}>
              <curInfo.Icon className="summary-icon" />
              <span>{curInfo.label}</span>
            </div>
            <div className="meta">
              {current.temperatureApparent != null && (
                <span title="Feels like temperature">Feels like: {Math.round(current.temperatureApparent)}{labels.temp}</span>
              )}
              <span title="Relative humidity">Humidity: {current.humidity != null ? Math.round(current.humidity) : "--"}%</span>
              <span title="Wind speed">Wind: {current.windSpeed != null ? Math.round(current.windSpeed) : "--"} {labels.speed}</span>
              {current.uvIndex != null && (
                <span title="UV index">UV: {Math.round(current.uvIndex)}</span>
              )}
              {current.visibility != null && (
                <span title="Visibility">Vis: {Math.round(current.visibility)} {distUnit}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {Array.isArray(hourly) && hourly.length > 0 && (
        <>
          <div className="section-title">Next 12 hours</div>
          <div className="weather-hourly">
            {hourly.slice(0, 12).map((h, idx) => {
              const info = codeToInfo(h.weatherCode);
              const t = new Date(h.time);
              const label = t.toLocaleTimeString([], { hour: 'numeric' });
              return (
                <div key={idx} className="hour">
                  <div className="h-time">{label}</div>
                  <div className="h-icon" title={info.label}><info.Icon /></div>
                  <div className="h-temp">{h.temperature != null ? Math.round(h.temperature) : "--"}{labels.temp}</div>
                  {h.precipitationProbability != null && (
                    <div className="h-pop" title="Precipitation chance">{Math.round(h.precipitationProbability)}%</div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      {Array.isArray(daily) && daily.length > 0 && (
        <>
          <div className="section-title">7-day forecast</div>
          <div className="weather-forecast">
          {daily.slice(0, 7).map((d, idx) => {
            const info = codeToInfo(d.weatherCodeMax);
            return (
              <div key={idx} className="weather-day" title={`${info.label} · Chance of precip: ${d.precipitationProbabilityAvg ?? "--"}%`}>
                <div className="day-name">{formatDate(d.date)}</div>
                <div className="day-icon" title={info.label}>
                  <info.Icon />
                </div>
                <div className="temps">
                  <span className="high">{d.temperatureMax != null ? Math.round(d.temperatureMax) : "--"}{labels.temp}</span>
                  <span className="low">{d.temperatureMin != null ? Math.round(d.temperatureMin) : "--"}{labels.temp}</span>
                </div>
                <div className="sun-row">
                  {d.sunriseTime && (
                    <span className="sun" title={`Sunrise · ${new Date(d.sunriseTime).toLocaleTimeString()}`}>
                      <WiSunrise /> {new Date(d.sunriseTime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                    </span>
                  )}
                  {d.sunsetTime && (
                    <span className="sun" title={`Sunset · ${new Date(d.sunsetTime).toLocaleTimeString()}`}>
                      <WiSunset /> {new Date(d.sunsetTime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                    </span>
                  )}
                </div>
                {d.uvIndexMax != null && (
                  <div className="uv" title="Max UV index">UV {Math.round(d.uvIndexMax)}</div>
                )}
              </div>
            );
          })}
          </div>
        </>
      )}

      {Array.isArray(hourly) && hourly.length > 0 && (
        <div className="weather-hourly">
          {hourly.slice(0, 12).map((h, idx) => {
            const info = codeToInfo(h.weatherCode);
            const t = new Date(h.time);
            const label = t.toLocaleTimeString([], { hour: 'numeric' });
            return (
              <div key={idx} className="hour">
                <div className="h-time">{label}</div>
                <div className="h-icon" title={info.label}><info.Icon /></div>
                <div className="h-temp">{h.temperature != null ? Math.round(h.temperature) : "--"}{labels.temp}</div>
                {h.precipitationProbability != null && (
                  <div className="h-pop" title="Precipitation chance">{Math.round(h.precipitationProbability)}%</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        .weather-card { display: flex; flex-direction: column; gap: 12px; }
        .weather-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
        .weather-location { font-weight: 600; font-size: 1rem; }
        .weather-time { color: #888; font-weight: 400; font-size: 0.85rem; margin-left: 6px; }
        .weather-now { display: flex; align-items: center; gap: 16px; }
        .weather-now .temp { font-size: 2rem; font-weight: 700; }
        .weather-now .now-right { display: flex; flex-direction: column; gap: 6px; }
        .weather-now .summary { display: flex; align-items: center; gap: 6px; color: #ddd; font-weight: 600; }
        .weather-now .summary-icon { font-size: 1.5rem; }
        .weather-now .meta { display: flex; gap: 12px; color: #aaa; font-size: 0.9rem; }
        .section-title { font-weight: 600; color: #cfe3ff; margin: 6px 0 4px; font-size: 0.95rem; }
        .weather-forecast { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; }
        .weather-day { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px; text-align: center; display: flex; flex-direction: column; gap: 6px; }
        .weather-day .day-name { font-size: 0.85rem; color: #bbb; margin-bottom: 6px; }
        .weather-day .day-icon { font-size: 1.5rem; color: #ddd; margin-bottom: 6px; }
        .weather-day .temps { display: flex; justify-content: center; gap: 8px; font-weight: 600; }
        .weather-day .high { color: #fff; }
        .weather-day .low { color: #9db1ff; }
        .weather-day .sun-row { display: flex; justify-content: center; gap: 10px; align-items: center; color: #ccc; font-size: 0.85rem; }
        .weather-day .sun { display: inline-flex; align-items: center; gap: 4px; }
        .weather-day .uv { color: #e9d66b; font-size: 0.8rem; font-weight: 600; }

        .weather-hourly { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(56px, 1fr); overflow-x: auto; gap: 8px; padding-top: 6px; }
        .weather-hourly .hour { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 6px; text-align: center; display: flex; flex-direction: column; gap: 4px; min-width: 64px; }
        .weather-hourly .h-time { color: #bbb; font-size: 0.85rem; }
        .weather-hourly .h-icon { font-size: 1.2rem; color: #ddd; }
        .weather-hourly .h-temp { font-weight: 700; }
        .weather-hourly .h-pop { color: #9db1ff; font-size: 0.8rem; }
      `}</style>
    </div>
  );
}
