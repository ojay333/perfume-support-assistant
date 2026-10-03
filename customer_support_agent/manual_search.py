import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from retrieval import load_index, rank_chunks

base_path = Path(__file__).resolve().parent
docs = base_path / "docs"
load_dotenv(base_path / ".env")

index_data = load_index(
    docs / "policy_index.json",
    docs / "exchange_policy.pdf",
    docs / "policy_chunks.json"
)

question = "هل توصلون الطلبات إلى جدة؟"

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

result = client.models.embed_content(
    model=index_data["metadata"]["model"],
    contents=question,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=index_data["metadata"]["dimension"]
    )
)

query_vector = result.embeddings[0].values

if len(query_vector) != index_data["metadata"]["dimension"]:
    raise ValueError("أبعاد متجه السؤال لا تطابق الفهرس")

matches = rank_chunks(query_vector, index_data["records"])

for match in matches:
    print(
        match["chunk_id"],
        "الصفحة:", match["page"],
        "التشابه:", round(match["score"], 3)
    )
    print(match["text"])
    print()
