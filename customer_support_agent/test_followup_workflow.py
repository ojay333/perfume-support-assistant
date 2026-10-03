from followup_workflow import process_followup
from unittest.mock import patch

valid_request = {
    "order_id": 5,
    "product_name": "عساف",
    "reason": "كسر في العبوة"
}

result = process_followup(valid_request)
assert result["status"] == "created"
assert result["ticket_id"] == 101

invalid_request = {
    "order_id": 5,
    "product_name": "عساف"
}

with patch("followup_workflow.create_ticket") as mocked_create_ticket:
    invalid_result = process_followup(invalid_request)

assert invalid_result["status"] == "error"
mocked_create_ticket.assert_not_called()

with patch(
    "followup_workflow.create_ticket",
    return_value={"status": "created"}
):
    incomplete_result = process_followup(valid_request)

assert incomplete_result["status"] == "error"
assert incomplete_result["message"] == "استجابة الخدمة لا تحتوي رقم الطلب"
