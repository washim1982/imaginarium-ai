from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.services.ocr_service import process_ocr


router = APIRouter(prefix="/api", tags=["OCR"])


@router.post("/ocr")
async def ocr_process(
    file: UploadFile = File(...),
    mode: str = Form("extract_text"),
):
    """
    Handles OCR / Image Description processing.
    mode = "extract_text" | "describe"
    """
    try:
        result = await process_ocr(file, mode)
        return JSONResponse(content={"text": result})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
