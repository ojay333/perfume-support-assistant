"""Explicit live smoke test: one embedding + one generation per question."""

import argparse
import json
import time

from rag_client import generate_grounded_reply


def main():
    parser = argparse.ArgumentParser(description="Live RAG smoke test (uses Gemini quota)")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    result = generate_grounded_reply(args.question)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("elapsed_seconds:", round(time.perf_counter() - started, 2))
    return 1 if result["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
