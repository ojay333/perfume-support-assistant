from followup import prepare_followup, execute_tool

product = {
    "order_id": 5,
    "product_name": "عساف",
    "reason": "كسر في العبوة"
}

result = prepare_followup(product)
assert result["status"] == "draft"

product_info = {
    "order_id": 5,
    "product_name": "عساف"
}

re = prepare_followup(product_info)
assert re["status"] == "error"

empty_reason = {
    "order_id": 5,
    "product_name": "عساف",
    "reason": ""
}

empty_result = prepare_followup(empty_reason)
assert empty_result["status"] == "error"

new_reas = {
    "order_id": 5,
    "product_name": "عساف",
    "reason": "   "
}
new_result = prepare_followup(new_reas)
assert new_result["status"] == "error"

new_prod = {
    "order_id": 5,
    "product_name": "   ",
    "reason": "كسر في العبوة"
}

new_empty_prodct = prepare_followup(new_prod)
assert new_empty_prodct["status"] == "error"

blocked_result = execute_tool("delete_order", product)
assert blocked_result["status"] == "error"
assert blocked_result["message"] == "الأداة غير مسموحة"

bad_arguments_result = execute_tool("prepare_followup", "بيانات")
assert bad_arguments_result["status"] == "error"
assert bad_arguments_result["message"] == "بيانات الأداة يجب أن تكون قاموسًا"

valid_tool_result = execute_tool("prepare_followup", product)
assert valid_tool_result["status"] == "draft"
assert valid_tool_result["order_id"] == 5

missing_data_result = execute_tool("prepare_followup", product_info)
assert missing_data_result["status"] == "error"
assert missing_data_result["message"] == "سبب طلب المتابعة مطلوب"

first_order_result = execute_tool("prepare_followup", {
    "order_id": 1,
    "product_name": "عساف",
    "reason": "كسر في العبوة"
})

assert first_order_result["status"] == "draft"

invalid_values = [
    ("order_id", -1),
    ("order_id", "5"),
    ("order_id", True),
    ("product_name", 123),
    ("reason", 123)
]

for field, value in invalid_values:
    invalid_request = product.copy()
    invalid_request[field] = value

    invalid_value_result = execute_tool(
        "prepare_followup", invalid_request
    )
    assert invalid_value_result["status"] == "error"
