from draft_schema import FollowupDraft
from pydantic import ValidationError

draft = FollowupDraft(
    product_name="عساف",
    reason="كسر في العبوة",
    order_id=None,
    title="متابعة عبوة مكسورة",
    description="وصلت عبوة عطر عساف مكسورة",
    missing_fields=["order_id"]
)

assert draft.order_id is None

try:
    FollowupDraft(
            product_name="عساف",
            reason="كسر في العبوة",
            title="متابعة عبوة مكسورة",
            description="وصلت عبوة عطر عساف مكسورة",
            missing_fields=["order_id"]
        )
    raise AssertionError("كان المفروض رفض الحقل الناقص")
except ValidationError:
    pass

try:
    FollowupDraft(
        product_name="عساف",
        order_id="خمسة",
        reason="كسر في العبوة",
        title="متابعة عبوة مكسورة",
        description="وصلت عبوة عطر عساف مكسورة",
        missing_fields=[]
    )
    raise AssertionError("كان المفروض رفض نوع رقم الطلب")
except ValidationError:
    pass

try:
    FollowupDraft(
        product_name="عساف",
        order_id=-5,
        reason="كسر في العبوة",
        title="متابعة عبوة مكسورة",
        description="وصلت عبوة عطر عساف مكسورة",
        missing_fields=[]
    )
    raise AssertionError("كان المفروض رفض رقم الطلب السالب")
except ValidationError:
    pass

raw_json = '{"product_name": "عساف", "order_id": null, "reason": "كسر في العبوة", "title": "متابعة عبوة مكسورة", "description": "وصلت عبوة عطر عساف مكسورة", "missing_fields": ["order_id"]}'

json_draft = FollowupDraft.model_validate_json(raw_json)
assert json_draft.order_id is None
assert draft.description == "وصلت عبوة عطر عساف مكسورة"
assert draft.missing_fields == ["order_id"]
