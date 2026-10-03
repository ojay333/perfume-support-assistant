from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

with patch(
    "api.generate_grounded_reply",
    return_value={"status": "success", "text": "رد تجريبي"}
):
    response = client.post(
        "/ask",
        json={"user_input": "ما سياسة الاستبدال؟"}
    )
    assert response.status_code == 200
    assert response.json()["text"] == "رد تجريبي"

with patch("api.generate_grounded_reply") as mock_reply:
    empty_response = client.post(
        "/ask",
        json={"user_input": "   "}
    )
    assert empty_response.status_code == 422
    mock_reply.assert_not_called()

with patch(
    "api.generate_grounded_reply",
    return_value={"status": "error", "message": "فشل تجريبي للخدمة"}
):
    error_response = client.post(
        "/ask",
        json={"user_input": "ما سياسة الاستبدال؟"}
    )
    assert error_response.status_code == 500
    assert error_response.json()["detail"] == "فشل تجريبي للخدمة"

with patch("api.generate_grounded_reply") as mock_reply:
    invalid_json_response = client.post(
        "/ask",
        content='{"user_input": ',
        headers={"Content-Type": "application/json"}
    )
    assert invalid_json_response.status_code == 422
    mock_reply.assert_not_called()

with patch(
    "api.generate_grounded_reply",
    return_value={"status": "success", "text": "رد تجريبي"}
) as mock_reply:
    allowed_response = client.post(
        "/ask", json={"user_input": "أ" * 500}
    )
    too_long_response = client.post(
        "/ask", json={"user_input": "أ" * 501}
    )
    assert allowed_response.status_code == 200
    assert too_long_response.status_code == 422
    mock_reply.assert_called_once()

draft_fixture = {
    "status": "draft",
    "data": {
        "order_id": 5,
        "product_name": "عساف",
        "reason": "كسر في العبوة",
        "title": "عبوة عطر مكسورة",
        "description": "استلم العميل عطر عساف بعبوة مكسورة.",
        "missing_fields": []
    }
}

with patch("api.generate_draft", return_value=draft_fixture):
    draft_response = client.post(
        "/requests",
        json={"user_input": "طلبي رقم 5، عطر عساف وصل مكسورًا"}
    )
    assert draft_response.status_code == 200
    assert draft_response.json() == draft_fixture

with patch(
    "api.generate_draft",
    return_value={"status": "error", "message": "فشل تجريبي للخدمة"}
):
    error_response = client.post(
        "/requests",
        json={"user_input": "ما سياسة الاستبدال؟"}
    )
    assert error_response.status_code == 500
    assert error_response.json()["detail"] == "فشل تجريبي للخدمة"

with patch(
    "api.generate_grounded_reply",
    return_value={"status": "insufficient_evidence", "text": "لا يوجد دليل كاف", "sources": []}
):
    absent = client.post("/ask", json={"user_input": "هل توصلون إلى جدة؟"})
    assert absent.status_code == 200
    assert absent.json()["status"] == "insufficient_evidence"
    assert absent.json()["sources"] == []
