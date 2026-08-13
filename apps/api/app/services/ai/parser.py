import json
from json import JSONDecodeError

from pydantic import ValidationError

from app.services.ai.base import AIResult
from app.services.ai.recommendation_schema import validate_recommendation

VALID_TYPES = {"weight", "running", "other"}


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        # ```json ... ``` 형태 제거
        text = text.split("\n", 1)[-1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _parse_json_object(raw: str) -> dict | None:
    """
    AI가 JSON 앞뒤에 설명문이나 코드블록을 붙여도 첫 번째 JSON 객체를 찾아 파싱한다.
    """
    text = _strip_code_fence(raw)

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (JSONDecodeError, ValueError):
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(text[index:])
        except JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    return None


def _is_json_like(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("```") or '"structured_data"' in stripped


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "추천", "recommendation"}
    return bool(value)


def _coerce_structured_data(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return _parse_json_object(value)
    return None


def _default_response_text(workout_type: str | None, structured_data: dict | None) -> str:
    title = structured_data.get("title") if structured_data else None
    if title:
        return f"{title} 루틴을 준비했어요. 아래 카드에서 확인하고 바로 기록할 수 있어요."
    if workout_type:
        return "요청에 맞춰 루틴을 준비했어요. 아래 카드에서 확인하고 바로 기록할 수 있어요."
    return "응답을 준비했어요."


def parse_ai_response(raw: str) -> AIResult:
    """
    AI 원시 응답(JSON 문자열)을 AIResult로 파싱한다.
    파싱 실패 시 structured_data 없이 텍스트만 반환해 챗봇이 최소한 동작하게 한다.
    """
    fallback_text = raw.strip() or "죄송해요, 응답을 만들지 못했어요. 다시 시도해 주세요."

    data = _parse_json_object(raw)
    if data is None:
        if _is_json_like(fallback_text):
            return AIResult(
                response_text=(
                    "루틴 응답 형식이 중간에 깨졌어요. 같은 요청을 한 번만 다시 보내주시면 "
                    "카드 형태로 다시 만들어드릴게요."
                ),
                workout_type=None,
                structured_data=None,
            )
        return AIResult(response_text=fallback_text, workout_type=None, structured_data=None)

    response_text = str(data.get("response_text") or fallback_text)

    # 간혹 AI가 response_text 안에 다시 JSON 객체를 문자열로 넣는 경우가 있다.
    nested_data = _parse_json_object(response_text) if _is_json_like(response_text) else None
    if nested_data and (
        "structured_data" in nested_data
        or "recommendation" in nested_data
        or nested_data.get("type") in VALID_TYPES
    ):
        data = nested_data
        response_text = str(data.get("response_text") or fallback_text)

    recommendation = data.get("recommendation")
    if isinstance(recommendation, dict):
        workout_type = recommendation.get("workout_type")
        structured_data = _coerce_structured_data(recommendation.get("structured_data"))
        is_recommendation = structured_data is not None
    elif data.get("type") in VALID_TYPES:
        workout_type = data.get("type")
        structured_data = data
        is_recommendation = True
    else:
        workout_type = data.get("workout_type")
        structured_data = _coerce_structured_data(data.get("structured_data"))
        is_recommendation = _coerce_bool(data.get("is_recommendation"))

    if workout_type not in VALID_TYPES and structured_data:
        workout_type = structured_data.get("type")

    if _is_json_like(response_text) and structured_data:
        response_text = _default_response_text(workout_type, structured_data)

    # 추천이 아니거나 형식이 어긋나면 structured_data를 버린다 (운동반영하기 입력 신뢰성 보장).
    if (
        not is_recommendation
        or workout_type not in VALID_TYPES
        or not isinstance(structured_data, dict)
        or structured_data.get("type") != workout_type
    ):
        return AIResult(response_text=response_text, workout_type=None, structured_data=None)

    try:
        validated_data = validate_recommendation(structured_data)
    except ValidationError:
        return AIResult(
            response_text=response_text,
            workout_type=None,
            structured_data=None,
        )

    return AIResult(
        response_text=response_text,
        workout_type=workout_type,
        structured_data=validated_data,
    )
