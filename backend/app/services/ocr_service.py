import os
import aiohttp
import asyncio
import json
import base64
from fastapi import UploadFile
from typing import Literal

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-dev:11434")
MODEL_NAME = os.getenv("VISION_MODEL", "aiden_lu/minicpm-v2.6:Q4_K_M")


async def process_ocr(file: UploadFile, mode: Literal["extract_text", "describe"] = "extract_text") -> str:
    """
    Performs OCR or image description using an Ollama vision model (llava).
    Falls back to mock output if Ollama isn't reachable.
    """
    try:
        file_bytes = await file.read()

        # Try real OCR via Ollama REST API
        try:
            async with aiohttp.ClientSession() as session:
                if mode == "extract_text":
                    prompt = (
                        "Act strictly as an OCR engine. Read every word, number, or symbol in this image and "
                        "output ONLY the characters you see in reading order. Use newline characters to match line "
                        "breaks. Do NOT describe the scene, objects, or colors. Do NOT add quotes, metadata, or commentary. "
                        "If absolutely no text exists, return the exact phrase NO TEXT FOUND."
                    )
                else:
                    prompt = "Describe this image in detail."
                encoded = base64.b64encode(file_bytes).decode("utf-8")
                data = {
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "images": [encoded],
                }
                async with session.post(f"{OLLAMA_HOST}/api/generate", json=data) as resp:
                    if resp.status != 200:
                        raise Exception(f"Ollama returned {resp.status}")
                    raw = await resp.text()
                    try:
                        payload = json.loads(raw)
                        txt = payload.get("response", "").strip()
                    except json.JSONDecodeError:
                        txt = raw.strip()
                    if mode == "extract_text":
                        stripped = txt.strip().strip('"')
                        if stripped.upper() == "NO TEXT FOUND":
                            return "NO TEXT FOUND"
                        return stripped
                    return txt

        except Exception as ollama_error:
            # Ollama not available → fallback to mock
            print(f"[OCR Service] Ollama not reachable: {ollama_error}")
            await asyncio.sleep(0.2)
            return _mock_ocr_result(file.filename, mode)

    except Exception as e:
        raise Exception(f"OCR processing failed: {e}")


def _mock_ocr_result(filename: str, mode: str) -> str:
    """
    Returns a mock OCR/description result for dev mode.
    """
    if mode == "extract_text":
        return f"[Mock OCR] Extracted text from '{filename}'."
    else:
        return f"[Mock Description] This image '{filename}' seems to contain text or objects."
