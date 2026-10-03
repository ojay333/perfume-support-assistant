from pathlib import Path
from tempfile import TemporaryDirectory
from retrieval import cosine_similarity, rank_chunks, load_index

assert cosine_similarity([1, 0], [2, 0]) == 1.0
assert cosine_similarity([0, 2], [1, 0]) == 0.0

try:
    cosine_similarity([0, 0], [1, 0])
    raise AssertionError("كان يجب رفض المتجه الصفري")
except ValueError:
    pass

try:
    cosine_similarity([1, 0], [0, 0])
    raise AssertionError("كان يجب رفض المتجه الصفري")
except ValueError:
    pass

fake_records = [
    {"chunk_id": "a", "page": 1, "text": "ألف", "vector": [0, 1]},
    {"chunk_id": "b", "page": 1, "text": "باء", "vector": [-1, 0]},
    {"chunk_id": "c", "page": 2, "text": "جيم", "vector": [1, 0]},
    {"chunk_id": "d", "page": 2, "text": "دال", "vector": [4, 3]},
]

result = rank_chunks([1, 0], fake_records)

assert len(result) == 3
assert result[0]["chunk_id"] == "c"
assert result[1]["chunk_id"] == "d"
assert result[2]["chunk_id"] == "a"

assert result[0]["page"] == 2
assert result[0]["text"] == "جيم"
assert result[0]["score"] == 1.0

assert len(rank_chunks([1, 0], fake_records, top_k=2)) == 2
assert rank_chunks([1, 0], []) == []

print("نجحت اختبارات ترتيب المقاطع")

docs = Path(__file__).parent / "docs"
index_path = docs / "policy_index.json"
pdf_path = docs / "exchange_policy.pdf"
chunks_path = docs / "policy_chunks.json"

loaded = load_index(index_path, pdf_path, chunks_path)
assert len(loaded["records"]) == 5

with TemporaryDirectory() as temp_dir:
    changed_pdf = Path(temp_dir) / "changed.pdf"
    changed_pdf.write_bytes(pdf_path.read_bytes() + b"\nchanged")

    try:
        load_index(index_path, changed_pdf, chunks_path)
        raise AssertionError("كان يجب رفض الفهرس القديم")
    except ValueError as error:
        assert str(error) == (
            "الفهرس قديم؛ أعد تجهيز المقاطع وبناء الفهرس"
        )

print("نجح تحميل الفهرس ورفض المصدر المعدل")
