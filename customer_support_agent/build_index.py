import os
import json
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import types
from policy_reader import read_policy, build_chunks



load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

chunks_path = os.path.join(
    os.path.dirname(__file__), "docs", "policy_chunks.json"
)

with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

pdf_path = os.path.join(
    os.path.dirname(__file__), "docs", "exchange_policy.pdf"
)

policy = read_policy(pdf_path)

if policy["status"] == "error":
    raise ValueError(policy["message"])

current_chunks = build_chunks(policy["page_texts"], 500)

if current_chunks != chunks:
    raise ValueError("ملف المقاطع قديم؛ أعد تشغيل prepare_policy.py")

with open(pdf_path, "rb") as f:
    pdf_hash = hashlib.sha256(f.read()).hexdigest()

with open(chunks_path, "rb") as f:
    chunks_hash = hashlib.sha256(f.read()).hexdigest()

texts = []
for chunk in chunks:
    texts.append(chunk["text"])

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=texts,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768,
    ),
)

vectors = []
for embedding in result.embeddings:
    vectors.append(embedding.values)

if len(vectors) != len(chunks):
    raise ValueError("عدد المتجهات لا يطابق عدد المقاطع")

for vector in vectors:
    if len(vector) != 768:
        raise ValueError("أبعاد المتجه غير صحيحة")

records = []

for index, chunk in enumerate(chunks):
    record = {
        "chunk_id": chunk["chunk_id"],
        "page": chunk["page"],
        "text": chunk["text"],
        "vector": vectors[index]
    }
    records.append(record)

index_data = {
    "metadata": {
        "model": "gemini-embedding-001",
        "dimension": 768,
        "pdf_sha256": pdf_hash,
        "chunks_sha256": chunks_hash
    },
    "records": records
}

index_path = os.path.join(
    os.path.dirname(__file__), "docs", "policy_index.json"
)

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(
        index_data, f,
        ensure_ascii=False,
        indent=2,
        allow_nan=False
    )

print(len(vectors))
print(len(vectors[0]))
