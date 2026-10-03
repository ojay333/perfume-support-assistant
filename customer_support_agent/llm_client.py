import os

import httpx
import httpx2
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from draft_schema import FollowupDraft
from pydantic import ValidationError
from followup import execute_tool

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

MAX_INPUT_CHARS = 500
MAX_OUTPUT_TOKENS = 500

SYSTEM_INSTRUCTION = """
أنت مساعد خدمة عملاء لمتجر عطور.
أجب باللغة العربية وبحد أقصى 4 جمل، ولا تخترع معلومات غير مذكورة هنا.

سياسة الاستبدال:
- الحالات المؤهلة: وصول المنتج مكسورًا أو تالفًا أو مختلفًا عن المطلوب.
- يجب تقديم طلب المتابعة خلال 3 أيام من استلام الطلب.
- يجب توفير رقم الطلب وصورة واضحة للمشكلة، والاحتفاظ بالعبوة وجميع أجزائها.
- لا تشمل السياسة التلف الناتج عن سوء الاستخدام، أو عدم الإعجاب بالرائحة إذا كان المنتج صحيحًا وسليمًا، أو الطلبات المقدمة بعد انتهاء المهلة.

صلاحياتك:
- يمكنك شرح السياسة والمساعدة في تجهيز مسودة طلب متابعة فقط.
- لا تقبل أو ترفض طلب الاستبدال، ولا تدّعِ إنشاء طلب أو إرساله إلى المتجر؛ لا توجد أداة لتنفيذ ذلك.
- لا تنفذ أو تعد باسترجاع الأموال أو أي عملية مالية.
- القرار النهائي يعود إلى موظف المتجر بعد مراجعة الطلب والأدلة.

استخدام الأداة:
- استخدم prepare_followup فقط عندما يطلب العميل صراحة تجهيز مسودة متابعة، ويذكر رقم الطلب واسم المنتج والسبب.
- إذا نقصت إحدى هذه البيانات، اسأل العميل عنها دون اختراعها ودون استدعاء الأداة.
- الإجابة عن أسئلة السياسة وحدها لا تحتاج إلى أداة.
- نتيجة draft تعني تجهيز مسودة فقط، ولا تعني إنشاء طلب خارجي أو الموافقة على الاستبدال.
- لا تطلب أكثر من استدعاء أداة واحد في الرد.
"""

DRAFT_INSTRUCTION = """
استخرج اسم المنتج ورقم الطلب وسبب المتابعة من رسالة العميل فقط.
لا تخترع معلومات غير مذكورة.
إذا غاب رقم الطلب استخدم null.
إذا غاب اسم المنتج أو السبب استخدم نصًا فارغًا للحقل المفقود.
هذه مسودة بيانات فقط؛ لا تنشئ طلبًا ولا تقرر قبوله أو رفضه ولا تنفذ عمليات مالية.
اكتب في حقل title عنوانًا مختصرًا يلخص مشكلة العميل، دون إضافة معلومات غير مذكورة.
اكتب في description وصفًا واضحًا للمشكلة اعتمادًا على المعلومات المذكورة فقط.
ضع في missing_fields أسماء الحقول غير المذكورة من: product_name وreason وorder_id. إذا كانت جميعها متوفرة، أعد قائمة فارغة [].
"""

FOLLOWUP_FUNCTION = types.FunctionDeclaration(
    name="prepare_followup",
    description="تجهز مسودة متابعة من رقم الطلب واسم المنتج والسبب، دون إنشاء طلب خارجي.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "order_id": {"type": "integer", "minimum": 1}, "product_name": {"type": "string"}, "reason": {"type": "string"}
        },
        "required": ["order_id", "product_name", "reason"],
    },
)

FOLLOWUP_TOOL = types.Tool(
    function_declarations=[FOLLOWUP_FUNCTION]
)

def generate_reply(user_input):
    if not isinstance(user_input, str) or not user_input.strip():
        return {"status": "error", "message": "النص مطلوب"}

    if len(user_input) > MAX_INPUT_CHARS:
        return {"status": "error", "message": "النص طويل جدا"}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
        "status": "error",
        "message": "مفتاح Gemini غير متاح"
        }

    try:
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_input.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[FOLLOWUP_TOOL],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.MINIMAL
                    )
                )
            )
    except (errors.APIError, httpx.HTTPError, httpx2.HTTPError, OSError):
        return {
            "status": "error",
            "message": "تعذر الاتصال بخدمة Gemini"
        }

    function_calls = response.function_calls or []
    if len(function_calls) > 1:
        return {"status": "error", "message": "يسمح باستدعاء أداة واحدة فقط"}

    tool_trace = None
    if function_calls:
        tool_call = function_calls[0]
        tool_result = execute_tool(tool_call.name, tool_call.args)
        if tool_result["status"] == "error":
            return tool_result
        tool_trace = {
            "name": tool_call.name,
            "result": tool_result
        }
        tool_response = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=tool_call.id,
                        name=tool_call.name,
                        response=tool_result
                    )
                )
            ]
        )
        conversation = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_input.strip())]
            ),
            response.candidates[0].content,
            tool_response
        ]

        try:
            with genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=30000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ) as client:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=conversation,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=[FOLLOWUP_TOOL],
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                        tool_config=types.ToolConfig(
                            function_calling_config=types.FunctionCallingConfig(
                                mode="NONE"
                            )
                        ),
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                        thinking_config=types.ThinkingConfig(
                            thinking_level=types.ThinkingLevel.MINIMAL
                        )
                    )
                )
        except (errors.APIError, httpx.HTTPError, httpx2.HTTPError, OSError):
            return {
                "status": "error",
                "message": "تعذر صياغة الرد بعد تجهيز المسودة"
            }

    if not response.text:
        return {
            "status": "error",
            "message": "لم تُرجع خدمة Gemini نصًا"
        }

    return {
        "status": "success",
        "text": response.text.strip(),
        "tool_trace": tool_trace
        }

def generate_draft(user_input):
    if not isinstance(user_input, str) or not user_input.strip():
        return {"status": "error", "message": "النص مطلوب"}

    if len(user_input) > MAX_INPUT_CHARS:
        return {"status": "error", "message": "النص طويل جدا"}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
        "status": "error",
        "message": "مفتاح Gemini غير متاح"
        }

    try:
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_input.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=DRAFT_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=FollowupDraft,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.MINIMAL
                    )
                )
            )
    except (errors.APIError, httpx.HTTPError, httpx2.HTTPError, OSError):
        return {
            "status": "error",
            "message": "تعذر الاتصال بخدمة Gemini"
        }

    if not response.text:
        return {
            "status": "error",
            "message": "لم تُرجع خدمة Gemini نصًا"
        }

    try:
        draft = FollowupDraft.model_validate_json(response.text)
    except ValidationError:
        return {
            "status": "error",
            "message": "رد Gemini لا يطابق قالب المسودة"
        }

    return {
        "status": "draft",
        "data": draft.model_dump()
    }
