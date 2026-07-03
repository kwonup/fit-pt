from datetime import date, timedelta

from fastapi import APIRouter, Depends
from app.core.deps import get_current_user_id, get_supabase
from supabase import Client

router = APIRouter()


@router.get("/weekly")
async def get_weekly_stats(
    weeks: int = 4,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    """주별 운동 시간(분) / 웨이트 볼륨(kg) / 러닝 거리(km)를 함께 반환한다."""
    weeks = 8 if weeks == 8 else 4

    result = supabase.rpc(
        "get_weekly_stats", {"p_user_id": user_id, "p_weeks": weeks}
    ).execute()

    return [
        {
            "week_start": row["week_start"],
            "total_minutes": row.get("total_minutes") or 0,
            "total_volume": row.get("total_volume") or 0,
            "total_distance_km": row.get("total_distance_km") or 0,
        }
        for row in (result.data or [])
    ]


@router.get("/summary")
async def get_summary(
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    result = (
        supabase.table("workout_sessions")
        .select("workout_date, duration_minutes")
        .eq("user_id", user_id)
        .order("workout_date", desc=True)
        .execute()
    )
    sessions = result.data
    this_week_minutes = sum(
        session.get("duration_minutes") or 0
        for session in sessions
        if date.fromisoformat(session["workout_date"]) >= this_week_start
    )

    return {
        "this_week_minutes": this_week_minutes,
        "total_sessions": len(sessions),
        "last_workout_date": sessions[0]["workout_date"] if sessions else None,
    }
