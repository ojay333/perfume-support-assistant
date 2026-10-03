import numpy as np
import json
import hashlib

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0  or np.linalg.norm(b) == 0:
        raise ValueError("لا يمكن مقارنة متجه صفري")
    score = np.dot(a, b) / (
    np.linalg.norm(a) * np.linalg.norm(b)
    )
    return score

def rank_chunks(query_vector, records, top_k=3):
    scored_records = []

    for record in records:
        score = cosine_similarity(query_vector, record["vector"])
        scored_records.append({
            "chunk_id": record["chunk_id"],
            "page": record["page"],
            "text": record["text"],
            "score": score
        })

    ordered = sorted(
        scored_records,
        key=lambda item: item["score"],
        reverse=True
        )
    return ordered[:top_k]

def load_index(index_path, pdf_path, chunks_path):
    with open(index_path, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    metadata = index_data["metadata"]

    with open(pdf_path, "rb") as f:
        pdf_hash = hashlib.sha256(f.read()).hexdigest()

    with open(chunks_path, "rb") as f:
        chunks_hash = hashlib.sha256(f.read()).hexdigest()

    if (
        metadata["pdf_sha256"] != pdf_hash
        or metadata["chunks_sha256"] != chunks_hash
    ):
        raise ValueError(
            "الفهرس قديم؛ أعد تجهيز المقاطع وبناء الفهرس"
        )

    if (
        metadata["model"] != "gemini-embedding-001"
        or metadata["dimension"] != 768
    ):
        raise ValueError("إعدادات الفهرس لا تطابق إعدادات البحث")

    return index_data


def build_context(matches):
    """Send source IDs and text, not similarity scores or model-made pages."""
    context_records = []
    for match in matches:
        context_records.append({
            "chunk_id": match["chunk_id"],
            "text": match["text"],
        })
    return context_records
