from llm_client import generate_reply, generate_draft
import os
import httpx
import httpx2
from unittest.mock import patch
from google.genai import errors, types

empty_result = generate_reply("")

assert empty_result["status"] == "error"
assert empty_result["message"] == "النص مطلوب"

long_result = generate_reply("ا" * 501)

assert long_result["status"] == "error"
assert long_result["message"] == "النص طويل جدا"

with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
    missing_key_result = generate_reply("ما سياسة الاسترجاع؟")

assert missing_key_result["status"] == "error"
assert missing_key_result["message"] == "مفتاح Gemini غير متاح"

fake_error = errors.APIError(
    500,
    {"message": "Internal error"}
)

with patch("llm_client.genai.Client", side_effect=fake_error):
    provider_error_result = generate_reply("ما سياسة الاسترجاع؟")

assert provider_error_result["status"] == "error"
assert provider_error_result["message"] == "تعذر الاتصال بخدمة Gemini"

fake_json = '{"product_name": "عساف", "order_id": null, "reason": "كسر في العبوة", "title": "متابعة عبوة مكسورة", "description": "وصلت عبوة عطر عساف مكسورة", "missing_fields": ["order_id"]}'

with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.return_value.text = fake_json

        draft_result = generate_draft("عطر عساف وصل مكسورًا")
        client.models.generate_content.return_value.text = (
            '{"product_name":"عساف","order_id":-5,"reason":"كسر في العبوة", "title": "متابعة عبوة مكسورة", "description": "وصلت عبوة عطر عساف مكسورة", "missing_fields": []}'
            )
        invalid_draft_result = generate_draft("عطر عساف وصل مكسورًا")

    assert draft_result["status"] == "draft"
    assert draft_result["data"]["title"] == "متابعة عبوة مكسورة"
    assert draft_result["data"]["order_id"] is None
    assert invalid_draft_result["status"] == "error"
    assert invalid_draft_result["message"] == "رد Gemini لا يطابق قالب المسودة"
    assert draft_result["data"]["description"] == "وصلت عبوة عطر عساف مكسورة"
    assert draft_result["data"]["missing_fields"] == ["order_id"]

expected_text = "هذا رد تجريبي عن السياسة."

with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.return_value.function_calls = []
        client.models.generate_content.return_value.text = expected_text

        with patch("llm_client.execute_tool") as mock_execute:
            no_tool_result = generate_reply("ما سياسة الاستبدال؟")
            mock_execute.assert_not_called()

        client.models.generate_content.assert_called_once()
        assert no_tool_result["status"] == "success"
        assert no_tool_result["text"] == expected_text

with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.return_value.function_calls = [
            types.FunctionCall(
                name="delete_order",
                args={"order_id": 5}
            )
        ]

        with patch("followup.prepare_followup") as mock_prepare:
            blocked_call_result = generate_reply("احذف الطلب رقم 5")
            mock_prepare.assert_not_called()

        client.models.generate_content.assert_called_once()
        assert blocked_call_result["status"] == "error"
        assert blocked_call_result["message"] == "الأداة غير مسموحة"


with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.return_value.function_calls = [
            types.FunctionCall(
                name="prepare_followup",
                args={"order_id": 5, "product_name": "عساف"}
            )
        ]

        missing_reason_result = generate_reply(
            "جهز مسودة متابعة للطلب 5، عطر عساف"
        )
        client.models.generate_content.assert_called_once()
        assert missing_reason_result["status"] == "error"
        assert missing_reason_result["message"] == "سبب طلب المتابعة مطلوب"

fake_call = types.FunctionCall(
    id="test-call-1",
    name="prepare_followup",
    args={
        "order_id": 5,
        "product_name": "عساف",
        "reason": "كسر في العبوة"
    }
)

fake_model_content = types.Content(
    role="model",
    parts=[types.Part(function_call=fake_call)]
)

fake_call_response = types.GenerateContentResponse(
    candidates=[types.Candidate(content=fake_model_content)]
)
expected_reply = "جهزت مسودة المتابعة، ولم يُنشأ طلب خارجي."

fake_final_content = types.Content(
    role="model",
    parts=[types.Part(text=expected_reply)]
)

fake_final_response = types.GenerateContentResponse(
    candidates=[types.Candidate(content=fake_final_content)]
)

with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.side_effect = [
            fake_call_response,
            fake_final_response
        ]

        success_result = generate_reply(
            "جهز مسودة متابعة للطلب 5، عطر عساف، بسبب كسر في العبوة"
        )
        assert client.models.generate_content.call_count == 2
        assert success_result["status"] == "success"
        assert success_result["text"] == expected_reply

        second_call = client.models.generate_content.call_args_list[1]
        sent_messages = second_call.kwargs["contents"]
        assert sent_messages[2].role == "user"
        sent_result = sent_messages[2].parts[0].function_response

        assert sent_result.name == "prepare_followup"
        assert sent_result.id == "test-call-1"
        assert sent_result.response["status"] == "draft"
        assert sent_result.response["order_id"] == 5

with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-only"}):
    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.return_value.function_calls = [
            fake_call,
            fake_call
        ]

        with patch("llm_client.execute_tool") as mock_execute:
            multiple_calls_result = generate_reply("جهز مسودتي متابعة")
            mock_execute.assert_not_called()

        client.models.generate_content.assert_called_once()

assert multiple_calls_result["status"] == "error"
assert multiple_calls_result["message"] == "يسمح باستدعاء أداة واحدة فقط"

assert no_tool_result["tool_trace"] is None
assert success_result["tool_trace"]["name"] == "prepare_followup"
assert success_result["tool_trace"]["result"]["status"] == "draft"

# Offline transport regressions: both SDK transports must yield a safe error.
for transport in (httpx, httpx2):
    for generate in (generate_reply, generate_draft):
        with patch("llm_client.genai.Client") as mock_client:
            client = mock_client.return_value.__enter__.return_value
            client.models.generate_content.side_effect = transport.ConnectError("offline fixture")
            result = generate("جهز مسودة متابعة تجريبية")
            assert result == {"status": "error", "message": "تعذر الاتصال بخدمة Gemini"}
            options = mock_client.call_args.kwargs["http_options"]
            assert options.timeout == 30000
            assert options.retry_options.attempts == 1

    with patch("llm_client.genai.Client") as mock_client:
        client = mock_client.return_value.__enter__.return_value
        client.models.generate_content.side_effect = [
            fake_call_response, transport.ReadTimeout("offline fixture"),
        ]
        result = generate_reply("جهز مسودة متابعة للطلب 5، عطر عساف، بسبب كسر في العبوة")
        assert result == {"status": "error", "message": "تعذر صياغة الرد بعد تجهيز المسودة"}
