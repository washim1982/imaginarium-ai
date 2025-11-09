from fastapi import APIRouter
from app.services.ollama_service import list_models


router = APIRouter(prefix="/api", tags=["Models"])


@router.get("/models")
def get_models():
    """Return available local Ollama models (no auth for dev)."""
    return {"models": list_models()}
