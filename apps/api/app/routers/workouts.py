from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.deps import get_current_user_id, get_supabase
from app.schemas.workouts import RunningWorkoutCreate, WeightWorkoutCreate, WorkoutSessionUpdate
from supabase import Client

router = APIRouter()


@router.get("")
async def list_workouts(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    query = supabase.table("workout_sessions").select("*").eq("user_id", user_id)
    if (year is None) != (month is None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="year와 month는 함께 전달해야 합니다.")

    if year is not None and month is not None:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        query = query.gte("workout_date", start.isoformat()).lte("workout_date", end.isoformat())

    result = query.order("workout_date", desc=True).execute()
    return result.data


@router.get("/{session_id}")
async def get_workout(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("workout_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    session = result.data
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="운동 기록이 없습니다.")

    if session["workout_type"] == "weight":
        exercises_result = (
            supabase.table("weight_exercises")
            .select("id, muscle_group, exercise_name, order_index, weight_sets(set_number, weight_kg, reps)")
            .eq("session_id", session_id)
            .order("order_index")
            .execute()
        )
        session["exercises"] = exercises_result.data
    elif session["workout_type"] == "running":
        running_result = (
            supabase.table("running_sessions")
            .select("distance_km, duration_minutes, avg_pace, intensity")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        session["running"] = running_result.data

    return session


@router.post("/weight", status_code=status.HTTP_201_CREATED)
async def create_weight_workout(
    body: WeightWorkoutCreate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    session_id = None
    try:
        session_payload = {
            "user_id": user_id,
            "workout_date": body.workout_date.isoformat(),
            "workout_type": "weight",
            "duration_minutes": body.duration_minutes,
            "memo": body.memo,
            "ai_recommendation_id": body.ai_recommendation_id,
        }
        session = supabase.table("workout_sessions").insert(session_payload).execute().data[0]
        session_id = session["id"]

        exercises = []
        for exercise in body.exercises:
            exercise_payload = {
                "session_id": session_id,
                "muscle_group": body.muscle_group,
                "exercise_name": exercise.exercise_name,
                "order_index": exercise.order_index,
            }
            created_exercise = supabase.table("weight_exercises").insert(exercise_payload).execute().data[0]
            set_payloads = [
                {
                    "exercise_id": created_exercise["id"],
                    "set_number": workout_set.set_number,
                    "weight_kg": workout_set.weight_kg,
                    "reps": workout_set.reps,
                }
                for workout_set in exercise.sets
            ]
            if set_payloads:
                created_exercise["weight_sets"] = supabase.table("weight_sets").insert(set_payloads).execute().data
            else:
                created_exercise["weight_sets"] = []
            exercises.append(created_exercise)

        session["exercises"] = exercises
        return session
    except Exception as exc:
        if session_id is not None:
            supabase.table("workout_sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="웨이트 기록 저장에 실패했습니다.") from exc


@router.post("/running", status_code=status.HTTP_201_CREATED)
async def create_running_workout(
    body: RunningWorkoutCreate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    session_id = None
    try:
        session_payload = {
            "user_id": user_id,
            "workout_date": body.workout_date.isoformat(),
            "workout_type": "running",
            "duration_minutes": body.duration_minutes,
            "memo": body.memo,
            "ai_recommendation_id": body.ai_recommendation_id,
        }
        session = supabase.table("workout_sessions").insert(session_payload).execute().data[0]
        session_id = session["id"]
        running = (
            supabase.table("running_sessions")
            .insert(
                {
                    "session_id": session_id,
                    "distance_km": body.distance_km,
                    "duration_minutes": body.duration_minutes,
                    "avg_pace": body.avg_pace,
                    "intensity": body.intensity,
                }
            )
            .execute()
            .data[0]
        )
        session["running"] = running
        return session
    except Exception as exc:
        if session_id is not None:
            supabase.table("workout_sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="러닝 기록 저장에 실패했습니다.") from exc


@router.put("/{session_id}")
async def update_workout(
    session_id: str,
    body: WorkoutSessionUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    existing = (
        supabase.table("workout_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if existing.data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="운동 기록이 없습니다.")

    allowed = body.model_dump(exclude_unset=True)
    if "workout_date" in allowed and allowed["workout_date"] is not None:
        allowed["workout_date"] = allowed["workout_date"].isoformat()
    if not allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="변경할 필드가 없습니다.")

    result = (
        supabase.table("workout_sessions")
        .update(allowed)
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data


@router.delete("/{session_id}")
async def delete_workout(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    result = (
        supabase.table("workout_sessions")
        .delete()
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="운동 기록이 없습니다.")
    return {"deleted": True}
