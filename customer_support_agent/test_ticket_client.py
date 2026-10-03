from ticket_client import create_ticket, validate_ticket_response
valid_draft = {
    "status": "draft",
    "order_id": 5,
    "product_name": "عساف",
    "reason": "كسر في العبوة"
}

result = create_ticket(valid_draft)
assert result["status"] == "created"

invalid_draft = {"status": "error"}

invalid_result = create_ticket(invalid_draft)
assert invalid_result["status"] == "error"

ticket_id = validate_ticket_response(result)
assert ticket_id == 101

incomplete_response = {
    "status": "created"
}

try:
    validate_ticket_response(incomplete_response)
    error_happened = False
except ValueError:
    error_happened = True

assert error_happened
