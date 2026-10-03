from followup import prepare_followup
from ticket_client import create_ticket, validate_ticket_response

def process_followup(request_data):
    draft = prepare_followup(request_data)

    if draft["status"] == "error":
        return draft

    ticket_response = create_ticket(draft)
    try:
        ticket_id = validate_ticket_response(ticket_response)
    except ValueError as error:
        return {
            "status": "error",
            "message": str(error)
        }

    return {
        "status": "created",
        "ticket_id": ticket_id
    }
