from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.security import require_user
from app.services.ollama_service import embeddings, generate
from app.services.rag_service import best_chunk
from docx import Document
from pypdf import PdfReader
import pandas as pd
import io
import json


router = APIRouter(prefix="/api", tags=["RAG"])


# In-memory per-user vector store
_RAG_STORE = {}


def _extract_text(filename: str, raw: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith((".docx", ".doc")):
        try:
            document = Document(io.BytesIO(raw))
            return "\n".join(para.text for para in document.paragraphs)
        except Exception as exc:
            raise ValueError("Unsupported DOC format. Please upload DOCX/PDF/TXT.") from exc
    if name.endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None)
        parts = []
        for sheet_name, df in sheets.items():
            parts.append(f"Sheet {sheet_name}:\n{df.to_csv(index=False)}")
        return "\n\n".join(parts)
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(raw)).to_csv(index=False)
    return raw.decode("utf-8", errors="ignore")


@router.post("/rag/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(require_user)):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        text = _extract_text(file.filename, raw).strip()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not text:
        raise HTTPException(status_code=400, detail="Unable to extract text from file")
    step = 500
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i:i+step]
        vec = (await embeddings("nomic-embed-text", chunk))["embedding"]
        chunks.append((chunk, vec))
    _RAG_STORE[user.sub] = chunks
    return {"chunks": len(chunks)}


@router.post("/rag/ask")
async def ask_question(payload: dict, user=Depends(require_user)):
    question = payload.get("question", "").strip()
    chunks = _RAG_STORE.get(user.sub)
    if not chunks:
        return {"error": "No document uploaded"}


    # Pick the most relevant chunk
    best = await best_chunk("nomic-embed-text", question, chunks)
    context_prompt = f"Answer the question using only this context:\n{best}\n\nQuestion: {question}"


    # Request streaming generation from Ollama
    session, resp = await generate("granite4:tiny-h", context_prompt, stream=True)


    async def stream_gen():
        async for line in resp.content:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if 'response' in data:
                    yield json.dumps({"response": data['response']}) + "\n"
            except Exception:
                continue
        await resp.release()
        await session.close()


    return StreamingResponse(stream_gen(), media_type="application/x-ndjson")
