import json
import os

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services.langsearch_service import LangSearchError, langsearch
from app.services import ollama_service as ollama
from app.services.weather_service import (
    WeatherError,
    realtime as weather_realtime,
    forecast as weather_forecast,
    forecast_hourly as weather_hourly,
)


router = APIRouter(prefix="/api", tags=["Chat"])
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-dev:11434")
SEARCH_TRIGGER = "NEEDS_SEARCH"
SYSTEM_INSTRUCTION = (
    "You are an assistant embedded in Imaginarium AI. Answer concisely using your training data. "
    "When you include code, return it as fenced Markdown code blocks with the correct language identifier (e.g., ```python, ```sql). "
    "If the question requires current/live information or anything you are unsure about, respond with ONLY the token "
    f"{SEARCH_TRIGGER}."
)


@router.post("/chat")
async def chat_endpoint(request: Request):
    try:
        body = await request.json()
        models = body.get("models", [])
        prompt = body.get("prompt", "")
        options = body.get("options", {}) or {}
        weather_units = (options.get("weatherUnits") or "").lower() or None

        if not models or not prompt:
            raise HTTPException(status_code=400, detail="Missing models or prompt")

        model = models[0]

        def _requires_live_data(user_prompt: str, model_text: str) -> bool:
            """Heuristic: decide if we should fall back to web search.

            Triggers when:
            - The prompt obviously asks for time-sensitive info (e.g., weather today, current price, latest news), or
            - The model response contains common disclaimers indicating lack of real-time knowledge.
            """
            p = (user_prompt or "").lower()
            m = (model_text or "").lower()

            # Obvious time-sensitive intents
            prompt_needles = [
                "weather", "forecast", "temperature", "today", "now", "current",
                "latest", "breaking", "news", "stock", "price", "exchange rate",
                "btc", "bitcoin", "eth", "traffic", "score", "game score", "live",
            ]
            if any(k in p for k in prompt_needles):
                return True

            # Model disclaimers that imply it couldn't answer live info
            response_flags = [
                "according to my training data",
                "i don't have real-time",
                "i do not have real-time",
                "i don't have browsing",
                "i cannot browse",
                "i can't browse",
                "cannot provide live updates",
                "can't provide live updates",
                "no real-time access",
                "i don't have access to current",
                "as an ai language model",
            ]
            return any(flag in m for flag in response_flags)

        def _is_weather_query(user_prompt: str) -> bool:
            p = (user_prompt or "").lower()
            needles = [
                "weather",
                "temperature",
                "forecast",
                "rain",
                "snow",
                "wind",
                "humidity",
                "uv index",
            ]
            return any(k in p for k in needles)

        def _extract_location(user_prompt: str) -> str | None:
            import re
            p = (user_prompt or "").strip()

            def _clean(term: str) -> str:
                term = term.strip().strip(",;:. ")
                # remove trailing time words like today/now/tonight/this week/tomorrow
                term = re.sub(
                    r"\b(?:today|now|tonight|tomorrow|this\s+(?:morning|afternoon|evening|week|weekend))\b\s*$",
                    "",
                    term,
                    flags=re.IGNORECASE,
                ).strip()
                term = term.strip(",;:. ")
                return term

            # capture phrase after in/at/for ...
            m = re.search(r"\b(?:in|at|for)\s+([A-Za-z\s,]+)$", p, flags=re.IGNORECASE)
            if m:
                loc = _clean(m.group(1))
                if loc:
                    return loc
            # fallback: try last 3 words as a place when user writes "weather denver today"
            words = re.findall(r"[A-Za-z]+", p)
            if words:
                tail = _clean(" ".join(words[-3:]))
                if tail:
                    return tail
            # accept explicit lat,lon
            m2 = re.search(r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)", p)
            if m2:
                return f"{m2.group(1)},{m2.group(2)}"
            return None

        def stream_response():
            try:
                # Let the UI know we're working on the answer.
                yield _encode(model, "Thinking…")

                first_prompt = f"{SYSTEM_INSTRUCTION}\n\nUser request:\n{prompt}"
                initial = _call_model(first_prompt, model)

                # If model signals search explicitly OR we detect it's a live query,
                # decide whether to use the weather API or generic web search.
                if not (
                    initial.strip() == SEARCH_TRIGGER
                    or _requires_live_data(prompt, initial)
                ):
                    yield _encode(model, initial)
                    return

                # Prefer dedicated weather API when the query is about weather.
                if _is_weather_query(prompt):
                    loc = _extract_location(prompt)
                    if not loc:
                        yield _encode(model, "Please specify a location (e.g., 'weather today in Boston, MA').")
                        return
                    yield _encode(model, f"Fetching live weather for {loc}…")
                    try:
                        current = weather_realtime(loc, weather_units)
                    except WeatherError as exc:
                        yield _encode(model, f"Weather service unavailable: {exc}")
                        return

                    # If geocoding resolved the input, let the user know the interpreted place.
                    resolved_label = current.get("resolved_label")
                    resolved_loc = current.get("resolved_location")
                    if resolved_label or (resolved_loc and (resolved_loc != loc)):
                        note = resolved_label or resolved_loc
                        yield _encode(model, f"Using location: {note}")

                    loc_for_forecast = resolved_loc or loc
                    daily = []
                    hourly = []
                    daily_err = None
                    hourly_err = None
                    try:
                        daily = weather_forecast(loc_for_forecast, weather_units)
                    except WeatherError as exc:
                        daily_err = str(exc)
                    try:
                        hourly = weather_hourly(loc_for_forecast, weather_units, hours=12)
                    except WeatherError as exc:
                        hourly_err = str(exc)

                    if daily_err or hourly_err:
                        msg = "Some forecast data unavailable: " + ", ".join(
                            [p for p in [f"daily: {daily_err}" if daily_err else None, f"hourly: {hourly_err}" if hourly_err else None] if p]
                        )
                        yield _encode(model, msg)

                    # Stream a typed payload so the UI can render a rich weather card.
                    yield _encode_obj({
                        "model": model,
                        "type": "weather",
                        "weather": {"current": current, "daily": daily, "hourly": hourly},
                    })
                    return

                # Need live data.
                yield _encode(model, "Fetching live search results…")
                try:
                    results = langsearch(prompt, top_k=5, summary=True, freshness="now:1h")
                except LangSearchError as exc:
                    yield _encode(model, f"Search unavailable: {exc}")
                    return

                if not results:
                    yield _encode(model, "No live data was found for this request.")
                    return

                snippets = []
                for idx, result in enumerate(results, start=1):
                    snippets.append(
                        f"{idx}. {result.get('title','')}\n{result.get('snippet','')}\n{result.get('url','')}"
                    )

                search_prompt = (
                    "You indicated you needed real-time information. Using ONLY the verified snippets below, answer the user's question. "
                    "If the snippets do not contain the required information, say so. Cite relevant facts but do not hallucinate.\n\n"
                    f"User question: {prompt}\n\n"
                    f"Search snippets:\n{chr(10).join(snippets)}\n\nAnswer:"
                )

                yield _encode(model, "Synthesizing answer from live snippets…")
                final_text = _call_model(search_prompt, model)
                yield _encode(model, final_text)

            except HTTPException as exc:
                yield _encode(model, f"Error: {exc.detail}")
            except Exception as exc:
                yield _encode(model, f"Unexpected error: {exc}")

        return StreamingResponse(stream_response(), media_type="application/x-ndjson")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _call_model(prompt: str, model: str) -> str:
    # Enforce residency policy: at most N models loaded; unload LRU if needed.
    try:
        ollama.ensure_capacity_before_use(model)
    except Exception:
        # Don't block on policy issues; proceed to call the model.
        pass
    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
    if resp.status_code != 200:
        try:
            err_payload = resp.json()
            message = err_payload.get("error") or err_payload
        except Exception:
            message = f"HTTP {resp.status_code} from model service"
        raise HTTPException(status_code=502, detail=message)
    data = resp.json()
    try:
        ollama.touch_model(model)
    except Exception:
        pass
    return data.get("response", "")


def _encode(model: str, text: str) -> str:
    return json.dumps({"model": model, "response": text}) + "\n"

def _encode_obj(payload: dict) -> str:
    return json.dumps(payload) + "\n"
