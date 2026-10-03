import json
from policy_reader import read_policy, build_chunks

policy = read_policy("customer_support_agent/docs/exchange_policy.pdf")

if policy["status"] == "error":
    raise ValueError(policy["message"])

chunks = build_chunks(policy["page_texts"], 500)

with open("customer_support_agent/docs/policy_chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

with open("customer_support_agent/docs/policy_chunks.json", "r", encoding="utf-8") as f:
    saved_chunks = json.load(f)

target_id = "p2-c1"

for chunk in saved_chunks:
    if chunk["chunk_id"] == target_id:
        print(chunk)
