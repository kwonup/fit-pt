from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any

from supabase import Client

TYPE_LABEL = {"weight": "웨이트", "running": "러닝", "other": "기타"}
MUSCLE_KEYWORDS = {
    "가슴": ["가슴", "벤치", "체스트", "푸시업", "딥스", "플라이"],
    "등": ["등", "랫풀", "로우", "풀업", "턱걸이", "데드"],
    "하체": ["하체", "스쿼트", "레그", "런지", "힙쓰러스트"],
    "어깨": ["어깨", "숄더", "사이드", "레터럴", "프레스"],
    "팔": ["팔", "이두", "삼두", "컬", "푸시다운"],
    "코어": ["코어", "복근", "플랭크", "크런치"],
}
PROFILE_COLUMNS = (
    "fitness_goals, fitness_level, main_workout_type, weekly_frequency, "
    "caution_areas, persona"
)
RECENT_SESSION_LIMIT = 5
MAX_MEMO_CHARS = 200


@dataclass(frozen=True)
class WorkoutContext:
    """Router가 선택한 사용자 데이터만 담는 AI 입력 컨텍스트."""

    profile: dict[str, Any] | None
    profile_context: str | None
    history_context: str | None

    def to_prompt(self) -> str:
        sections = [
            section
            for section in (self.profile_context, self.history_context)
            if section
        ]
        return "\n".join(sections)


class WorkoutContextProvider:
    """인증된 user_id로 프로필과 운동 기록을 선택적으로 조회한다."""

    def __init__(self, supabase: Client) -> None:
        self.supabase = supabase

    def load(
        self,
        user_id: str,
        message: str = "",
        *,
        use_profile: bool,
        use_history: bool,
    ) -> WorkoutContext:
        if not user_id.strip():
            raise ValueError("운동 컨텍스트 조회에는 user_id가 필요합니다.")

        profile = self._fetch_profile(user_id) if use_profile else None
        profile_context = build_profile_context(profile) if use_profile else None
        history_context = (
            build_workout_history_context(self.supabase, user_id, message)
            if use_history
            else None
        )
        return WorkoutContext(profile, profile_context, history_context)

    def _fetch_profile(self, user_id: str) -> dict[str, Any] | None:
        result = (
            self.supabase.table("user_profiles")
            .select(PROFILE_COLUMNS)
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None


def _message_has_any(message: str, keywords: list[str]) -> bool:
    return any(keyword in message for keyword in keywords)


def _detect_muscle_keywords(message: str) -> list[str]:
    matched: list[str] = []
    for muscle, keywords in MUSCLE_KEYWORDS.items():
        if _message_has_any(message, keywords):
            matched.extend(keywords)
    return matched


def _detect_days_ago(message: str) -> int | None:
    if "지난주" in message or "저번주" in message:
        return 7
    if "2주 전" in message or "2주전" in message:
        return 14
    if "3주 전" in message or "3주전" in message:
        return 21

    match = re.search(r"(\d+)\s*(일|주)\s*전", message)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    return amount * 7 if unit == "주" else amount


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


def _format_weight_session_detail(session: dict) -> str | None:
    exercises = session.get("weight_exercises") or []
    if not exercises:
        return None

    exercise_parts: list[str] = []
    for exercise in exercises[:6]:
        sets = exercise.get("weight_sets") or []
        set_texts: list[str] = []
        for workout_set in sets[:5]:
            weight = _fmt_kg(workout_set.get("weight_kg"))
            reps = workout_set.get("reps")
            if reps is None:
                set_texts.append(f"{weight}kg")
            else:
                set_texts.append(f"{weight}kg×{reps}")
        if set_texts:
            exercise_parts.append(f"{exercise.get('exercise_name')}: {', '.join(set_texts)}")
        else:
            exercise_parts.append(str(exercise.get("exercise_name")))

    if not exercise_parts:
        return None

    title = f" '{session['title']}'" if session.get("title") else ""
    return f"{session['workout_date']}{title} - " + " / ".join(exercise_parts)


def _format_recent_session(session: dict[str, Any]) -> str:
    workout_type = session["workout_type"]
    parts = [
        str(session["workout_date"]),
        TYPE_LABEL.get(workout_type, workout_type),
    ]
    if session.get("title"):
        parts.append(f"'{session['title']}'")
    if session.get("duration_minutes") is not None:
        parts.append(f"{session['duration_minutes']}분")

    running = session.get("running_sessions")
    if isinstance(running, list):
        running = running[0] if running else None
    if workout_type == "running" and isinstance(running, dict):
        if running.get("distance_km") is not None:
            parts.append(f"{_fmt_number(running['distance_km'])}km")
        if running.get("avg_pace"):
            parts.append(f"평균 페이스 {running['avg_pace']}/km")
        if running.get("intensity"):
            parts.append(f"강도 {running['intensity']}")

    memo = _compact_memo(session.get("memo"))
    if memo:
        parts.append(f"메모: {memo}")
    return " ".join(parts)


def _fmt_number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def _compact_memo(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    compacted = re.sub(r"\s+", " ", value).strip()
    if not compacted:
        return None
    if len(compacted) <= MAX_MEMO_CHARS:
        return compacted
    return compacted[:MAX_MEMO_CHARS].rstrip() + "…"


def _fetch_weight_session_details(
    supabase: Client,
    user_id: str,
    *,
    days: int = 90,
    limit: int = 5,
    target_days_ago: int | None = None,
    exercise_keywords: list[str] | None = None,
) -> list[str]:
    cutoff_date = date.today() - timedelta(days=days)
    query = (
        supabase.table("workout_sessions")
        .select(
            "id, workout_date, title, weight_exercises("
            "exercise_name, order_index, weight_sets(set_number, weight_kg, reps)"
            ")"
        )
        .eq("user_id", user_id)
        .eq("workout_type", "weight")
        .gte("workout_date", cutoff_date.isoformat())
        .order("workout_date", desc=True)
        .limit(20)
    )

    rows = query.execute().data or []

    if target_days_ago is not None:
        target_date = date.today() - timedelta(days=target_days_ago)

        def distance_from_target(row: dict) -> int:
            workout_date = date.fromisoformat(row["workout_date"])
            return abs((workout_date - target_date).days)

        rows = sorted(rows, key=distance_from_target)

    if exercise_keywords:
        lowered_keywords = [keyword.lower() for keyword in exercise_keywords]

        def matches_keywords(row: dict) -> bool:
            title = str(row.get("title") or "").lower()
            exercises = row.get("weight_exercises") or []
            exercise_names = " ".join(str(ex.get("exercise_name") or "").lower() for ex in exercises)
            haystack = f"{title} {exercise_names}"
            return any(keyword in haystack for keyword in lowered_keywords)

        matched_rows = [row for row in rows if matches_keywords(row)]
        rows = matched_rows or rows

    details: list[str] = []
    for row in rows[:limit]:
        detail = _format_weight_session_detail(row)
        if detail:
            details.append(detail)
    return details


def _build_dynamic_weight_context(supabase: Client, user_id: str, message: str) -> list[str]:
    message = message.strip()
    sections: list[str] = []

    wants_recent_detail = _message_has_any(message, ["지난번", "이전", "최근", "똑같", "동일", "비슷"])
    wants_best = _message_has_any(message, ["최고", "최고기록", "최대", "pr", "PR"])
    days_ago = _detect_days_ago(message)
    muscle_keywords = _detect_muscle_keywords(message)

    if not any([wants_recent_detail, wants_best, days_ago is not None, muscle_keywords]):
        return sections

    if days_ago is not None:
        details = _fetch_weight_session_details(
            supabase,
            user_id,
            days=max(days_ago + 21, 45),
            limit=3,
            target_days_ago=days_ago,
            exercise_keywords=muscle_keywords,
        )
        if details:
            sections.append(f"- 요청 기간 근처 웨이트 상세({days_ago}일 전 기준): " + " | ".join(details))

    if wants_recent_detail or muscle_keywords:
        details = _fetch_weight_session_details(
            supabase,
            user_id,
            days=90,
            limit=5,
            exercise_keywords=muscle_keywords,
        )
        if details:
            label = "관련 최근 웨이트 상세" if muscle_keywords else "최근 웨이트 상세"
            sections.append(f"- {label}: " + " | ".join(details))

    if wants_best:
        sections.append("- 최고기록 요청: 종목별 중량 기록의 '최고' 값을 기준으로 하되, 안전한 증량 폭을 적용한다.")

    return sections


def build_profile_context(profile: dict[str, Any] | None) -> str:
    """프로필을 AI가 읽기 쉬운 최소 필드로 변환한다."""
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

    return "\n".join(lines)


def build_workout_history_context(
    supabase: Client,
    user_id: str,
    message: str = "",
) -> str:
    """최근 30일 운동 요약과 질문에 필요한 웨이트 상세를 만든다."""
    lines: list[str] = []

    cutoff = (date.today() - timedelta(days=30)).isoformat()
    result = (
        supabase.table("workout_sessions")
        .select(
            "workout_date, workout_type, title, duration_minutes, memo, "
            "running_sessions(distance_km, avg_pace, intensity)"
        )
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

    recent = sessions[:RECENT_SESSION_LIMIT]
    recent_str = "; ".join(_format_recent_session(session) for session in recent)
    lines.append(f"- 최근 운동 내역: {recent_str}")

    if weight_history:
        lines.append(f"- 종목별 중량 기록(전체): {weight_history}")

    dynamic_sections = _build_dynamic_weight_context(supabase, user_id, message)
    lines.extend(dynamic_sections)

    return "\n".join(lines)


def build_user_context(
    supabase: Client,
    user_id: str,
    profile: dict | None,
    message: str = "",
) -> str:
    """기존 챗봇 계약을 유지하는 프로필 + 운동 기록 컨텍스트 wrapper."""
    return "\n".join(
        (
            build_profile_context(profile),
            build_workout_history_context(supabase, user_id, message),
        )
    )
