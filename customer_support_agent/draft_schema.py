from pydantic import BaseModel, Field

class FollowupDraft(BaseModel):
    product_name: str
    reason: str
    order_id: int | None = Field(ge=1)
    title: str
    description: str
    missing_fields: list[str]
