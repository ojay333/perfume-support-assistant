from policy_reader import read_policy, split_text
from unittest.mock import Mock, patch
from policy_reader import read_policy, split_text, build_chunks

the_policy = read_policy("customer_support_agent/docs/exchange_policy.pdf")
assert the_policy["status"] == "success" and the_policy["pages"] == 2

wrong_policy = read_policy("customer_support_agent/docs/missing.pdf")
assert wrong_policy["status"] == "error"
assert len(the_policy["page_texts"]) == 2
assert the_policy["page_texts"][1]["page"] == 2

empty_page = Mock()
empty_page.extract_text.return_value = ""

fake_reader = Mock()
fake_reader.pages = [empty_page]

with patch("policy_reader.pypdf.PdfReader", return_value=fake_reader):
    empty_policy = read_policy("empty.pdf")
    assert empty_policy["status"] == "success"
    assert empty_policy["page_texts"][0]["text"] == ""

chunks_result = split_text("abcdefghij", 4)
assert chunks_result == ["abcd", "efgh", "ij"]

empty_chunks = split_text("", 4)
assert empty_chunks == []

exact_chunks = split_text("abcd", 4)
assert exact_chunks == ["abcd"]

demo_pages = [
    {"page": 2, "text": "abc"},
    {"page": 5, "text": "defgh"}
]

linked_chunks = build_chunks(demo_pages, 4)

expected_chunks = [
    {"chunk_id": "p2-c1", "page": 2, "text": "abc"},
    {"chunk_id": "p5-c1", "page": 5, "text": "defg"},
    {"chunk_id": "p5-c2", "page": 5, "text": "h"}
]

assert linked_chunks == expected_chunks

pages_with_gap = [
    {"page": 1, "text": "abcd"},
    {"page": 2, "text": ""},
    {"page": 3, "text": "efgh"}
]

gap_chunks = build_chunks(pages_with_gap, 4)
assert len(gap_chunks) == 2
assert gap_chunks[1]["page"] == 3

pdf_chunks = build_chunks(the_policy["page_texts"], 500)

print(len(pdf_chunks))
print(pdf_chunks[0])

assert "خلال 3 أيام" in the_policy["page_texts"][0]["text"]
assert "أكثر من 3 أيام" in the_policy["page_texts"][0]["text"]
assert "بعد 5 أيام" in the_policy["page_texts"][1]["text"]
assert "المسودة بحالة draft" in the_policy["page_texts"][1]["text"]
