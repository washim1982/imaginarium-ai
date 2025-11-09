import aiohttp, os, base64, requests, time, threading


# Prefer docker service hostname so containers can talk without extra env.
_DEFAULT_OLLAMA = "http://ollama-dev:11434"
_LOCALHOST_FALLBACK = "http://localhost:11434"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", _DEFAULT_OLLAMA)
_DEFAULT_MODELS_CSV = os.getenv("DEFAULT_MODELS", "")
MAX_LOADED_MODELS = int(os.getenv("MAX_LOADED_MODELS", "2") or 2)
KEEP_ALIVE_DEFAULT = os.getenv("OLLAMA_KEEP_ALIVE", "5m")  # hint to Ollama to unload when idle

# Simple in-process LRU tracker for last-used model timestamps
_LRU_LAST_USED: dict[str, float] = {}
_LRU_LOCK = threading.Lock()


def _configured_model_fallback():
    """
    Build a deterministic list of models from env configuration so the UI
    still has sensible options even if Ollama has no local tags yet.
    """
    seeds = []
    # Allow comma separated DEFAULT_MODELS plus specific feature flags.
    if _DEFAULT_MODELS_CSV:
        seeds.extend(_DEFAULT_MODELS_CSV.split(","))
    for env_var in ("VISION_MODEL", "TRANSLATION_MODEL"):
        value = os.getenv(env_var)
        if value:
            seeds.append(value)

    deduped = []
    seen = set()
    for raw in seeds:
        candidate = raw.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _host_candidates():
    """Yield configured host plus sane fallbacks (deduped)."""
    seen = set()
    for host in (OLLAMA_HOST, _LOCALHOST_FALLBACK):
        if host and host not in seen:
            seen.add(host)
            yield host


async def generate(model: str, prompt: str, stream: bool = True, options: dict | None = None):
    payload = {"model": model, "prompt": prompt, "stream": stream}
    if options:
        payload["options"] = options
    # Pass keep_alive hint if not provided via options
    if not options or "keep_alive" not in options:
        payload.setdefault("keep_alive", KEEP_ALIVE_DEFAULT)

    last_exc = None
    for host in _host_candidates():
        session = aiohttp.ClientSession()
        try:
            resp = await session.post(f"{host}/api/generate", json=payload)
            return session, resp
        except Exception as exc:
            last_exc = exc
            await session.close()
    raise RuntimeError(f"Unable to reach Ollama: {last_exc}")


async def embeddings(model: str, text: str):
    last_exc = None
    for host in _host_candidates():
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(f"{host}/api/embeddings", json={"model": model, "prompt": text}) as r:
                    return await r.json()
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Unable to reach Ollama for embeddings: {last_exc}")


def encode_image(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")

def list_models():
    """
    Returns a list of locally available Ollama models.
    Uses the Ollama REST API: GET /api/tags
    """
    errors = []
    for host in _host_candidates():
        try:
            resp = requests.get(f"{host}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                names = [m["name"] for m in data.get("models", [])]
                if names:
                    return names
                # Otherwise keep checking other hosts for tags.
                continue
            errors.append(f"{host} -> HTTP {resp.status_code}")
        except Exception as e:
            errors.append(f"{host} -> {e}")
    fallback = _configured_model_fallback()
    if fallback:
        return fallback
    if errors:
        return [f"Error contacting Ollama: {'; '.join(errors)}"]
    return []


# ------ Runtime model residency management ------

def list_loaded_models() -> list[str]:
    """Return names of models currently loaded in memory (ollama ps)."""
    errors = []
    for host in _host_candidates():
        try:
            r = requests.get(f"{host}/api/ps", timeout=5)
            if r.status_code == 200:
                data = r.json() or {}
                procs = data.get("models") or data.get("processes") or []
                names = []
                for p in procs:
                    name = p.get("name") or p.get("model")
                    if name:
                        names.append(name)
                return names
            errors.append(f"{host} -> HTTP {r.status_code}")
        except Exception as e:
            errors.append(f"{host} -> {e}")
    return []


def unload_model(name: str) -> bool:
    """Request Ollama to unload a model from memory (ollama stop)."""
    for host in _host_candidates():
        # Try both payload shapes for compatibility
        for body in ({"name": name}, {"model": name}):
            try:
                r = requests.post(f"{host}/api/stop", json=body, timeout=5)
                if r.status_code in (200, 204):
                    with _LRU_LOCK:
                        _LRU_LAST_USED.pop(name, None)
                    return True
            except Exception:
                continue
    return False


def touch_model(model: str) -> None:
    with _LRU_LOCK:
        _LRU_LAST_USED[model] = time.time()


def ensure_capacity_before_use(requested: str, limit: int | None = None) -> None:
    """
    Ensure at most `limit` models are resident before using `requested`.
    If a different model would exceed the limit, unload the least recently used.
    """
    lim = MAX_LOADED_MODELS if limit is None else limit
    if lim <= 0:
        return
    loaded = list_loaded_models()
    # Update LRU timestamp for requested (intent to use)
    touch_model(requested)
    if requested in loaded:
        return
    if len(loaded) < lim:
        return
    # Choose LRU among loaded (excluding the requested which isn't loaded)
    with _LRU_LOCK:
        candidates = [(m, _LRU_LAST_USED.get(m, 0.0)) for m in loaded]
    if not candidates:
        return
    candidates.sort(key=lambda t: t[1])
    victim = candidates[0][0]
    if victim and victim != requested:
        unload_model(victim)


def create_model_tag(name: str, base: str, adapter_path: str | None = None, params: dict | None = None) -> dict:
    """Create or overwrite an Ollama model tag via REST /api/create.

    If adapter_path exists, include ADAPTER line; otherwise create an alias with FROM base.
    Returns a dict { ok: bool, detail: str }.
    """
    content = [f"FROM {base}"]
    if adapter_path and os.path.exists(adapter_path):
        content.append(f"ADAPTER {adapter_path}")
    if params and isinstance(params, dict):
        for k, v in params.items():
            content.append(f"PARAM {k} {v}")
    modelfile = "\n".join(content) + "\n"
    payload = {"name": name, "modelfile": modelfile}
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/create", json=payload, timeout=120)
        if r.status_code >= 400:
            return {"ok": False, "detail": f"HTTP {r.status_code}: {r.text}"}
        return {"ok": True, "detail": "created"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def ensure_model_tag(name: str, base: str, adapter_path: str | None = None) -> dict:
    """Ensure a tag exists; create alias if missing."""
    existing = list_models()
    if isinstance(existing, list) and name in existing:
        return {"ok": True, "detail": "exists"}
    return create_model_tag(name, base, adapter_path)
