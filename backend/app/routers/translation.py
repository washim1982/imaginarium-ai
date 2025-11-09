from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.translation_service import process_translation


router = APIRouter(prefix="/api", tags=["Translation & Summary"])


@router.post("/translation")
async def translate_text(
    language: str = Form("English"),
    file: UploadFile = File(...),
):
    """
    Handles text translation and summarization.
    Expects an uploaded .txt file (e.g. Arabic text),
    and returns both translated and summarized versions.
    """
    try:
        result = await process_translation(file, language)
        return {
            "original": result["original"],
            "translation": result["translation"],
            "summary": result["summary"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
