from fastapi import APIRouter, Depends
from app.core.deps import get_current_user_id, get_supabase
from app.schemas.chat import ChatRequest
from supabase import Client

router = APIRouter()


@router.post("")
async def send_message(
    body: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    """
    AI 챗봇 메시지 전송.

    흐름:
    1. 사용자 프로필 + 최근 30일 기록 조회
    2. OpenAI API 호출 (페르소나 반영)
    3. 운동 추천인 경우 structured_data 파싱
    4. ai_recommendations 및 chat_messages 저장
    5. 응답 반환
    """
    # TODO: 전체 흐름 구현 (Phase 4)
    _ = body.message
    return {
        "message_id": "placeholder",
        "response_text": "AI 챗봇 기능 구현 예정입니다.",
        "recommendation": None,
    }
