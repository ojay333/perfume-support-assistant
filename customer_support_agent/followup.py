def prepare_followup(request_data):
    order_id = request_data.get("order_id")
    product_name = request_data.get("product_name")
    reason = request_data.get("reason")

    if not order_id:
        return {"status": "error", "message": "رقم الطلب مطلوب"}

    if type(order_id) is not int or order_id <= 0:
        return {
            "status": "error",
            "message": "رقم الطلب يجب أن يكون عددًا صحيحًا موجبًا"
        }

    if not isinstance(product_name, str) or not product_name.strip():
        return {"status": "error", "message": "اسم المنتج مطلوب"}

    if not isinstance(reason, str) or not reason.strip():
        return {"status": "error", "message": "سبب طلب المتابعة مطلوب"}

    return{
        "status": "draft",
        "order_id": order_id,
        "product_name": product_name,
        "reason": reason
    }

def execute_tool(tool_name, arguments):
    if tool_name != "prepare_followup":
        return {"status": "error", "message": "الأداة غير مسموحة"}
    if not isinstance(arguments, dict):
        return {"status": "error", "message": "بيانات الأداة يجب أن تكون قاموسًا"}

    return prepare_followup(arguments)
