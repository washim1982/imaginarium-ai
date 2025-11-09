from fastapi import APIRouter, UploadFile, File, Depends
from app.core.security import require_user
from app.services.analysis_service import preview_table, bar_png
from app.utils.file_validation import validate_file, ALLOWED_DOC_MIME
from app.stores.uploaded_data_store import uploaded_data_store
from io import BytesIO
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/api", tags=["Analysis"])


@router.post("/analysis/upload")
async def upload(file: UploadFile = File(...), user=Depends(require_user)):
    ok, msg = validate_file(file.content_type, 0, ALLOWED_DOC_MIME)
    if not ok: return {"error": msg}
    b = await file.read()
    preview, cols = preview_table(b, file.filename)
    uploaded_data_store[user.sub] = {"bytes": b, "filename": file.filename, "preview": preview, "cols": cols}
    return {"preview": preview, "columns": cols}


@router.get("/analysis/chart")
async def chart(x: str, y: str, user=Depends(require_user)):
    data = uploaded_data_store.get(user.sub)
    if not data: return {"error":"No data uploaded"}
    import pandas as pd, io
    b = data["bytes"]; fn = data["filename"]
    df = pd.read_csv(BytesIO(b)) if fn.endswith('.csv') else pd.read_excel(BytesIO(b))
    png = bar_png(df, x, y)
    return StreamingResponse(BytesIO(png), media_type="image/png")
