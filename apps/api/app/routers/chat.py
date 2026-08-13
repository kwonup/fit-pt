import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import get_current_user_id, get_supabase
from app.schemas.chat import ChatRequest
from app.services.ai.orchestrator import build_ai_orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("")
async def send_message(
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    """
    AI 챗봇 메시지 전송.

    질문 분류 → 필요한 SQL/RAG 조회 → AI provider 호출 → 추천 저장 → 응답 반환.
    """
    try:
        orchestration = await build_ai_orchestrator(supabase).run(user_id, body.message)
    except Exception as exc:
        logger.exception("AI orchestration failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 응답 생성에 실패했습니다.",
        ) from exc

    result = orchestration.ai_result

    # 추천이면 기존 카드/운동반영하기 계약에 맞춰 저장한다.
    recommendation = None
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
        recommendation = {
            "id": rec["id"],
            "workout_type": result.workout_type,
            "structured_data": result.structured_data,
        }

    return {
        # 현재 message_id는 프런트엔드 목록 key로만 사용하므로 DB ID가 필요하지 않다.
        "message_id": str(uuid4()),
        "response_text": result.response_text,
        "recommendation": recommendation,
    }
