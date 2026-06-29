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
    weeks = 8 if weeks == 8 else 4
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday())
    first_week_start = this_week_start - timedelta(weeks=weeks - 1)

    result = (
        supabase.table("workout_sessions")
        .select("workout_date, duration_minutes")
        .eq("user_id", user_id)
        .gte("workout_date", first_week_start.isoformat())
        .lte("workout_date", today.isoformat())
        .execute()
    )

    totals = {
        (first_week_start + timedelta(weeks=index)).isoformat(): 0
        for index in range(weeks)
    }
    for session in result.data:
        workout_date = date.fromisoformat(session["workout_date"])
        week_start = workout_date - timedelta(days=workout_date.weekday())
        key = week_start.isoformat()
        if key in totals:
            totals[key] += session.get("duration_minutes") or 0

    return [
        {"week_start": week_start, "total_minutes": total_minutes}
        for week_start, total_minutes in totals.items()
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
