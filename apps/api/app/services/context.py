from collections import Counter
from datetime import date, timedelta

from supabase import Client

TYPE_LABEL = {"weight": "웨이트", "running": "러닝", "other": "기타"}


def _fmt_kg(value) -> str:
    """80.0 -> '80', 77.5 -> '77.5' 형태로 깔끔하게 표기."""
    if value is None:
        return "-"
    num = float(value)
    return str(int(num)) if num.is_integer() else str(num)


def _build_weight_history(supabase: Client, user_id: str) -> str | None:
    """종목별 역대 최고 / 최근 작업 중량을 한 줄 요약으로 만든다. 기록 없으면 None."""
    try:
        result = supabase.rpc(
            "get_weight_exercise_maxes", {"p_user_id": user_id}
        ).execute()
    except Exception:
        # 함수 미배포 등으로 실패해도 추천 자체는 막지 않는다.
        return None

    rows = result.data or []
    if not rows:
        return None

    parts: list[str] = []
    for r in rows:
        name = r.get("exercise_name") or "?"
        best = f"최고 {_fmt_kg(r.get('best_weight_kg'))}kg"
        if r.get("best_reps") is not None:
            best += f"×{r['best_reps']}"
        recent = f"최근 {_fmt_kg(r.get('recent_weight_kg'))}kg"
        if r.get("recent_reps") is not None:
            recent += f"×{r['recent_reps']}"
        parts.append(f"{name}({best}, {recent})")

    return "; ".join(parts)


def build_user_context(supabase: Client, user_id: str, profile: dict | None) -> str:
    """AI에 전달할 사용자 컨텍스트(프로필 + 최근 30일 운동 요약) 문자열을 만든다."""
    lines: list[str] = []

    if profile:
        goals = ", ".join(profile.get("fitness_goals") or []) or "미설정"
        cautions = ", ".join(profile.get("caution_areas") or []) or "없음"
        lines.append(f"- 운동 목표: {goals}")
        lines.append(f"- 숙련도: {profile.get('fitness_level') or '미설정'}")
        lines.append(f"- 주 운동 타입: {profile.get('main_workout_type') or '미설정'}")
        lines.append(f"- 주당 운동 횟수: {profile.get('weekly_frequency') or '미설정'}")
        lines.append(f"- 주의/부상 부위: {cautions}")
    else:
        lines.append("- 프로필 미설정 (일반적인 기준으로 추천)")

    cutoff = (date.today() - timedelta(days=30)).isoformat()
    result = (
        supabase.table("workout_sessions")
        .select("workout_date, workout_type, title, duration_minutes")
        .eq("user_id", user_id)
        .gte("workout_date", cutoff)
        .order("workout_date", desc=True)
        .limit(30)
        .execute()
    )
    sessions = result.data or []

    weight_history = _build_weight_history(supabase, user_id)

    if not sessions:
        lines.append("- 최근 30일 운동 기록 없음")
        if weight_history:
            lines.append(f"- 종목별 중량 기록(전체): {weight_history}")
        return "\n".join(lines)

    type_counts = Counter(TYPE_LABEL.get(s["workout_type"], s["workout_type"]) for s in sessions)
    summary = ", ".join(f"{label} {count}회" for label, count in type_counts.items())
    lines.append(f"- 최근 30일 운동: 총 {len(sessions)}회 ({summary})")

    recent = sessions[:5]
    recent_str = "; ".join(
        f"{s['workout_date']} {TYPE_LABEL.get(s['workout_type'], s['workout_type'])}"
        + (f" '{s['title']}'" if s.get("title") else "")
        for s in recent
    )
    lines.append(f"- 최근 운동 내역: {recent_str}")

    if weight_history:
        lines.append(f"- 종목별 중량 기록(전체): {weight_history}")

    return "\n".join(lines)
