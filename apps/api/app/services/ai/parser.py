import json

from app.services.ai.base import AIResult

VALID_TYPES = {"weight", "running", "other"}


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        # ```json ... ``` 형태 제거
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def parse_ai_response(raw: str) -> AIResult:
    """
    AI 원시 응답(JSON 문자열)을 AIResult로 파싱한다.
    파싱 실패 시 structured_data 없이 텍스트만 반환해 챗봇이 최소한 동작하게 한다.
    """
    fallback_text = raw.strip() or "죄송해요, 응답을 만들지 못했어요. 다시 시도해 주세요."

    try:
        data = json.loads(_strip_code_fence(raw))
    except (json.JSONDecodeError, ValueError):
        return AIResult(response_text=fallback_text, workout_type=None, structured_data=None)

    if not isinstance(data, dict):
        return AIResult(response_text=fallback_text, workout_type=None, structured_data=None)

    response_text = str(data.get("response_text") or fallback_text)
    is_recommendation = bool(data.get("is_recommendation"))
    workout_type = data.get("workout_type")
    structured_data = data.get("structured_data")

    # 추천이 아니거나 형식이 어긋나면 structured_data를 버린다 (운동반영하기 입력 신뢰성 보장).
    if (
        not is_recommendation
        or workout_type not in VALID_TYPES
        or not isinstance(structured_data, dict)
        or structured_data.get("type") != workout_type
    ):
        return AIResult(response_text=response_text, workout_type=None, structured_data=None)

    return AIResult(
        response_text=response_text,
        workout_type=workout_type,
        structured_data=structured_data,
    )
