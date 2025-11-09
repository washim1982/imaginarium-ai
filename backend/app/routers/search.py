from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.langsearch_service import langsearch, LangSearchError


router = APIRouter(prefix="/api", tags=["Search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="User question to search for")
    limit: int = Field(5, ge=1, le=10)


@router.post("/search")
async def search_endpoint(payload: SearchRequest):
    try:
        results = langsearch(payload.query.strip(), payload.limit)
        return {"query": payload.query.strip(), "results": results}
    except LangSearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LangSearch failure: {exc}")
