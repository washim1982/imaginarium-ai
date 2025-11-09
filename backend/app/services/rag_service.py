import math
from typing import List, Tuple
from app.services.ollama_service import embeddings


def cosine(a: List[float], b: List[float]):
    num = sum(x*y for x, y in zip(a, b))
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return num / (da*db + 1e-9)


async def best_chunk(model: str, question: str, chunks: List[Tuple[str, List[float]]]):
    qv = (await embeddings(model, question))["embedding"]
    ranked = sorted(chunks, key=lambda c: cosine(qv, c[1]), reverse=True)
    return ranked[0][0] if ranked else ""