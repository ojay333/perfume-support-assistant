TICKET_RESPONSE_FIXTURE = {
    "status": "created",
    "ticket_id": 101
    }

def create_ticket(ticket_data):
    draft_status = ticket_data.get("status")

    if draft_status != "draft":
        return {
            "status": "error",
            "message": "الطلب ليس مسودة صالحة"
        }

    return TICKET_RESPONSE_FIXTURE.copy()

def validate_ticket_response(response):
    ticket_id = response.get("ticket_id")

    if not ticket_id:
        raise ValueError("استجابة الخدمة لا تحتوي رقم الطلب")
    return ticket_id
