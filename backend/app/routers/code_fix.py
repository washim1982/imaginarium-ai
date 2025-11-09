from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.code_fix_service import run_code_fix


router = APIRouter(prefix="/api", tags=["Code Fix"])


@router.post("/codefix")
async def code_fix_endpoint(
    file: UploadFile = File(...),
    model: str = Form("granite4:tiny-h"),
):
    try:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read file: {exc}") from exc

    result = run_code_fix(file.filename, content, model)
    return {
        "filename": file.filename,
        "model": model,
        **result,
    }
