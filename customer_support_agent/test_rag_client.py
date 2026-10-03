"""Offline RAG tests: fake SDK results only; no Gemini request or index rebuild.

Run beside rag_client.py and retrieval.py: python test_rag_client.py
These fixtures check plumbing and source validation, not live answer quality.
"""

import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import httpx2
from google.genai import errors

from rag_client import GroundedAnswer, generate_grounded_reply, resolve_answer
from retrieval import build_context


MATCHES = [
    {
        "chunk_id": "p1-c1",
        "page": 1,
        "text": "تُقدم متابعة المنتج التالف خلال 3 أيام من الاستلام.",
        "score": 0.9,
    },
    {
        "chunk_id": "p2-c1",
        "page": 2,
        "text": "المسودة لا تعني الموافقة على الاستبدال.",
        "score": 0.8,
    },
]
FAKE_INDEX = {
    "metadata": {"model": "gemini-embedding-001", "dimension": 768},
    "records": [
        {
            "chunk_id": match["chunk_id"],
            "page": match["page"],
            "text": match["text"],
            "vector": vector,
        }
        for match, vector in zip(
            MATCHES,
            ([1.0] + [0.0] * 767, [0.0, 1.0] + [0.0] * 766),
        )
    ],
}


def config_value(config, name):
    return config.get(name) if isinstance(config, dict) else getattr(config, name)


class ContextTests(unittest.TestCase):
    def test_context_preserves_only_ids_and_text_in_input_order(self):
        matches = copy.deepcopy(MATCHES)
        original = copy.deepcopy(matches)

        self.assertEqual(
            build_context(matches),
            [
                {"chunk_id": match["chunk_id"], "text": match["text"]}
                for match in MATCHES
            ],
        )
        self.assertEqual(matches, original)

    def test_empty_context(self):
        self.assertEqual(build_context([]), [])


class ResolveAnswerTests(unittest.TestCase):
    def test_success_uses_retrieved_source_data_and_trims_answer(self):
        answer = GroundedAnswer(
            has_answer=True,
            answer="  المسودة ليست موافقة نهائية.  ",
            chunk_ids=["p2-c1"],
        )

        self.assertEqual(
            resolve_answer(answer, MATCHES),
            {
                "status": "success",
                "text": "المسودة ليست موافقة نهائية.",
                "sources": [
                    {
                        "chunk_id": "p2-c1",
                        "page": 2,
                        "text": MATCHES[1]["text"],
                    }
                ],
            },
        )

    def test_answer_requires_retrieved_sources_and_nonblank_text(self):
        cases = [
            ("unknown_source", "جواب", ["p1-c1", "p99-c9"]),
            ("missing_sources", "جواب", []),
            ("empty_answer", "", ["p1-c1"]),
            ("blank_answer", " \n\t", ["p1-c1"]),
        ]
        for label, text, ids in cases:
            with self.subTest(case=label):
                answer = GroundedAnswer(
                    has_answer=True, answer=text, chunk_ids=ids
                )
                with self.assertRaises(ValueError):
                    resolve_answer(answer, MATCHES)

    def test_no_evidence_ignores_generated_claim_and_invented_source(self):
        baseline = resolve_answer(
            GroundedAnswer(has_answer=False, answer="", chunk_ids=[]), MATCHES
        )
        untrusted = resolve_answer(
            GroundedAnswer(
                has_answer=False,
                answer="تم تحويل المبلغ إلى حسابك.",
                chunk_ids=["p99-c9"],
            ),
            MATCHES,
        )

        self.assertEqual(untrusted, baseline)
        self.assertEqual(untrusted["status"], "insufficient_evidence")
        self.assertEqual(untrusted["sources"], [])
        self.assertTrue(untrusted["text"].strip())
        self.assertRegex(untrusted["text"], r"[\u0600-\u06ff]")
        self.assertNotIn("تم تحويل المبلغ", untrusted["text"])


class GenerateGroundedReplyTests(unittest.TestCase):
    def setUp(self):
        # All external boundaries are replaced, including the local index load.
        client_patcher = patch("rag_client.genai.Client")
        self.client_factory = client_patcher.start()
        self.addCleanup(client_patcher.stop)
        index_patcher = patch("rag_client.load_index")
        self.load_index = index_patcher.start()
        self.addCleanup(index_patcher.stop)
        getenv_patcher = patch(
            "rag_client.os.getenv", return_value="test-only-not-a-key"
        )
        self.getenv = getenv_patcher.start()
        self.addCleanup(getenv_patcher.stop)
        self.call_order = Mock()
        self.call_order.attach_mock(self.load_index, "load_index")
        self.call_order.attach_mock(self.client_factory, "client")
        self.load_index.return_value = copy.deepcopy(FAKE_INDEX)
        self.client = self.client_factory.return_value.__enter__.return_value
        self.client.models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[1.0] + [0.0] * 767)]
        )
        self.client.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps(
                {
                    "has_answer": True,
                    "answer": "  تقدم المتابعة خلال 3 أيام.  ",
                    "chunk_ids": ["p1-c1"],
                },
                ensure_ascii=False,
            )
        )

    def test_invalid_inputs_do_not_load_index_or_create_client(self):
        cases = [None, 42, "", " \n\t", "ا" * 501]
        for value in cases:
            with self.subTest(
                value_type=type(value).__name__,
                value_length=len(value) if isinstance(value, str) else None,
            ):
                self.assertEqual(generate_grounded_reply(value)["status"], "error")
        self.load_index.assert_not_called()
        self.client_factory.assert_not_called()

    def test_missing_key_does_not_create_client(self):
        self.getenv.return_value = None
        result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
        self.assertEqual(result["status"], "error")
        self.client_factory.assert_not_called()

    def test_success_sends_json_context_without_tools_and_resolves_sources(self):
        question = "ما مهلة تقديم المتابعة؟"
        result = generate_grounded_reply(question)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "تقدم المتابعة خلال 3 أيام.")
        self.assertEqual(
            result["sources"],
            [{"chunk_id": "p1-c1", "page": 1, "text": MATCHES[0]["text"]}],
        )
        self.load_index.assert_called_once()
        self.client_factory.assert_called_once()
        calls = [call[0] for call in self.call_order.mock_calls]
        self.assertLess(calls.index("load_index"), calls.index("client"))

        self.client.models.embed_content.assert_called_once()
        embed_call = self.client.models.embed_content.call_args.kwargs
        self.assertEqual(embed_call["model"], "gemini-embedding-001")
        self.assertEqual(
            config_value(embed_call["config"], "task_type"), "RETRIEVAL_QUERY"
        )
        self.assertEqual(
            config_value(embed_call["config"], "output_dimensionality"), 768
        )

        self.client.models.generate_content.assert_called_once()
        generate_call = self.client.models.generate_content.call_args.kwargs
        prompt = json.loads(generate_call["contents"])
        self.assertEqual(
            prompt,
            {"question": question, "context": build_context(MATCHES)},
        )
        config = generate_call["config"]
        self.assertFalse(config_value(config, "tools"))
        self.assertEqual(
            config_value(config, "response_mime_type"), "application/json"
        )
        self.assertIs(config_value(config, "response_schema"), GroundedAnswer)

    def test_stale_index_stops_before_client_creation(self):
        self.load_index.side_effect = ValueError("الفهرس قديم")
        result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
        self.assertEqual(result["status"], "error")
        self.client_factory.assert_not_called()

    def test_empty_index_returns_no_evidence_without_client(self):
        self.load_index.return_value["records"] = []
        result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])
        self.assertTrue(result["text"].strip())
        self.client_factory.assert_not_called()

    def test_invalid_query_vectors_stop_before_text_generation(self):
        cases = {
            "dimension_mismatch": [1.0] + [0.0] * 766,
            "zero_vector": [0.0] * 768,
            "nonfinite_vector": [float("nan")] + [0.0] * 767,
        }
        for label, vector in cases.items():
            with self.subTest(case=label):
                self.client.models.embed_content.return_value = SimpleNamespace(
                    embeddings=[SimpleNamespace(values=vector)]
                )
                result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
                self.assertEqual(result["status"], "error")
                self.client.models.generate_content.assert_not_called()

    def test_malformed_or_empty_model_response_returns_error(self):
        for response_text in ('{"has_answer": ', "", " \n", None):
            with self.subTest(response=response_text):
                self.client.models.generate_content.return_value = SimpleNamespace(
                    text=response_text
                )
                result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
                self.assertEqual(result["status"], "error")

    def test_provider_errors_at_either_call_return_error(self):
        for operation in ("embed_content", "generate_content"):
            with self.subTest(operation=operation):
                method = getattr(self.client.models, operation)
                method.side_effect = errors.APIError(500, {"message": "Internal error"})
                try:
                    result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
                    self.assertEqual(result["status"], "error")
                finally:
                    method.side_effect = None

    def test_transport_errors_at_either_call_return_error(self):
        for error_class in (httpx.ConnectError, httpx2.ConnectError):
            for operation in ("embed_content", "generate_content"):
                with self.subTest(
                    transport=error_class.__module__, operation=operation
                ):
                    method = getattr(self.client.models, operation)
                    method.side_effect = error_class("Offline test fixture")
                    try:
                        result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
                        self.assertEqual(result["status"], "error")
                    finally:
                        method.side_effect = None

    def test_generated_unknown_source_returns_error(self):
        self.client.models.generate_content.return_value.text = json.dumps(
            {
                "has_answer": True,
                "answer": "تقدم المتابعة خلال 3 أيام.",
                "chunk_ids": ["p99-c9"],
            },
            ensure_ascii=False,
        )
        result = generate_grounded_reply("ما مهلة تقديم المتابعة؟")
        self.assertEqual(result["status"], "error")
        self.assertFalse(result.get("sources"))


if __name__ == "__main__":
    unittest.main()
