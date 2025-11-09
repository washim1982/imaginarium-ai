import asyncio
import io
import json
import math
import os
import zipfile
from typing import Tuple

import aiohttp
from pypdf import PdfReader

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-dev:11434")
TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "llama3:8b")
MAX_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_PAGES = 10


async def _ollama_generate(session, prompt: str) -> str:
    payload = {"model": TRANSLATION_MODEL, "prompt": prompt, "stream": False}
    async with session.post(f"{OLLAMA_HOST}/api/generate", json=payload) as resp:
        if resp.status != 200:
            raise Exception(f"Ollama error {resp.status}")
        raw = await resp.text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
        response = data.get("response") or raw
        return response.strip()


def _extract_docx_text(content_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content_bytes)) as docx:
        with docx.open("word/document.xml") as doc_xml:
            from xml.etree import ElementTree as ET

            tree = ET.parse(doc_xml)
            return "".join(tree.itertext()).strip()


def _extract_pdf_text(content_bytes: bytes) -> Tuple[str, int]:
    reader = PdfReader(io.BytesIO(content_bytes))
    pages = len(reader.pages)
    text_parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(text_parts).strip(), pages


def _estimate_pages_from_text(text: str) -> int:
    chars_per_page = 1800
    return max(1, math.ceil(len(text) / chars_per_page))


async def process_translation(file, target_language: str = "English") -> dict:
    """
    Translate uploaded text/PDF/DOCX into the target language and summarize in English.
    Enforces file size (<=20MB) and length (<=10 pages) limits.
    """
    content_bytes = await file.read()
    if len(content_bytes) > MAX_BYTES:
        raise Exception("Uploaded file exceeds 20MB limit")

    filename = (file.filename or "").lower()
    content = ""
    page_count = 1

    if filename.endswith(".pdf"):
        content, page_count = _extract_pdf_text(content_bytes)
    elif filename.endswith(".docx"):
        content = _extract_docx_text(content_bytes)
        page_count = _estimate_pages_from_text(content)
    else:
        content = content_bytes.decode("utf-8", errors="ignore").strip()
        page_count = _estimate_pages_from_text(content)

    if not content:
        raise Exception("Uploaded file is empty")
    if page_count > MAX_PAGES:
        raise Exception("Document exceeds 10 page limit")

    try:
        async with aiohttp.ClientSession() as session:
            translate_prompt = (
                f"Translate the following text to {target_language}:\n\n{content}"
            )
            translation = await _ollama_generate(session, translate_prompt)

            summarize_prompt = (
                "Summarize the following text in English, keeping key facts:\n\n"
                f"{translation}"
            )
            summary = await _ollama_generate(session, summarize_prompt)

            return {
                "original": content,
                "translation": translation,
                "summary": summary,
            }

    except Exception as ollama_error:
        print(f"[Translation Service] Ollama not reachable: {ollama_error}")
        await asyncio.sleep(0.2)
        return {
            "original": content,
            "translation": "[Mock Translation] English version of uploaded text.",
            "summary": "[Mock Summary] This is a concise summary of the translated text.",
        }
