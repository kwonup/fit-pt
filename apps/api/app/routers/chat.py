from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.chat import ChatRequest
from app.services.ai.factory import get_provider
from app.services.ai.parser import parse_ai_response
from app.services.ai.prompts import build_system_prompt, build_user_prompt
from app.services.context import build_user_context

router = APIRouter()


@router.post("")
async def send_message(
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    """
    AI 챗봇 메시지 전송.

    프로필 + 최근 30일 기록 → AI provider(OpenAI/Claude) 호출 → structured_data 파싱
    → ai_recommendations / chat_messages 저장 → 응답 반환.
    """
    # 1. 사용자 프로필 조회 (없어도 진행)
    profile_result = (
        supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    )
    profile = profile_result.data[0] if profile_result.data else None
    persona = (profile or {}).get("persona", "angel")

    # 2. 컨텍스트 구성 + AI 호출
    context = build_user_context(supabase, user_id, profile)
    system_prompt = build_system_prompt(persona)
    user_prompt = build_user_prompt(context, body.message)

    try:
        raw = get_provider().generate(system_prompt, user_prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 응답 생성에 실패했습니다.",
        ) from exc

    result = parse_ai_response(raw)

    # 3. 사용자 메시지 저장
    supabase.table("chat_messages").insert(
        {"user_id": user_id, "role": "user", "content": body.message}
    ).execute()

    # 4. 추천이면 ai_recommendations 저장
    recommendation = None
    recommendation_id = None
    if result.structured_data is not None and result.workout_type is not None:
        rec = (
            supabase.table("ai_recommendations")
            .insert(
                {
                    "user_id": user_id,
                    "user_message": body.message,
                    "ai_response_text": result.response_text,
                    "structured_data": result.structured_data,
                    "workout_type": result.workout_type,
                }
            )
            .execute()
            .data[0]
        )
        recommendation_id = rec["id"]
        recommendation = {
            "id": rec["id"],
            "workout_type": result.workout_type,
            "structured_data": result.structured_data,
        }

    # 5. AI 응답 메시지 저장 (추천이면 recommendation_id 연결)
    assistant_message = (
        supabase.table("chat_messages")
        .insert(
            {
                "user_id": user_id,
                "role": "assistant",
                "content": result.response_text,
                "recommendation_id": recommendation_id,
            }
        )
        .execute()
        .data[0]
    )

    return {
        "message_id": assistant_message["id"],
        "response_text": result.response_text,
        "recommendation": recommendation,
    }
