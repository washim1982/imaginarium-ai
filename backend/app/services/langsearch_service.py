import os
import requests


LANGSEARCH_API_URL = os.getenv("LANGSEARCH_API_URL", "https://api.langsearch.ai/v1/web-search")
LANGSEARCH_API_KEY = os.getenv("LANGSEARCH_API_KEY")

# Optional fallback provider (Tavily)
TAVILY_API_URL = os.getenv("TAVILY_API_URL", "https://api.tavily.com/search")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


class LangSearchError(Exception):
    """Raised when LangSearch configuration or response is invalid."""


def _normalize_results(raw_items):
    normalized = []
    for item in raw_items:
        normalized.append(
            {
                "title": item.get("title") or item.get("name") or "",
                "url": item.get("url") or item.get("link") or item.get("source", ""),
                "snippet": item.get("snippet")
                or item.get("summary")
                or item.get("content")
                or item.get("description")
                or "",
            }
        )
    return normalized


def langsearch(query: str, top_k: int = 5, summary: bool = False, freshness: str | None = None) -> list[dict]:
    if not query:
        raise LangSearchError("Query cannot be empty")

    # 1) Primary: LangSearch
    if LANGSEARCH_API_KEY:
        payload = {"query": query, "count": top_k, "summary": summary}
        if freshness:
            payload["freshness"] = freshness
        headers = {
            "Authorization": f"Bearer {LANGSEARCH_API_KEY}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(LANGSEARCH_API_URL, json=payload, headers=headers, timeout=20)
            if resp.status_code < 400:
                data = resp.json()
                results = (
                    data.get("value")
                    or data.get("results")
                    or data.get("items")
                    or data.get("data")
                    or []
                )
                return _normalize_results(results)
            # fall through to try Tavily if configured
        except requests.RequestException:
            # fall through to try Tavily if configured
            pass

    # 2) Fallback: Tavily (if key configured)
    if TAVILY_API_KEY:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TAVILY_API_KEY}"}
        body = {
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": max(1, int(top_k)),
        }
        try:
            resp = requests.post(TAVILY_API_URL, json=body, headers=headers, timeout=20)
            if resp.status_code < 400:
                data = resp.json() or {}
                items = data.get("results") or []
                # Map Tavily results to our normalized schema
                mapped = [
                    {
                        "title": it.get("title", ""),
                        "url": it.get("url", ""),
                        "snippet": it.get("content", ""),
                    }
                    for it in items
                ]
                return mapped
        except requests.RequestException:
            pass

    # If we get here, no provider succeeded.
    if not LANGSEARCH_API_KEY and not TAVILY_API_KEY:
        raise LangSearchError("No search provider configured (set LANGSEARCH_API_KEY or TAVILY_API_KEY)")
    raise LangSearchError("All configured search providers are unreachable")
