from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.services.ai.base import AIProvider
from app.services.ai.factory import get_provider

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    CHAT = "CHAT"
    WORKOUT_HISTORY = "WORKOUT_HISTORY"
    FITNESS_KNOWLEDGE = "FITNESS_KNOWLEDGE"
    PERSONAL_COACHING = "PERSONAL_COACHING"
    ROUTINE_RECOMMENDATION = "ROUTINE_RECOMMENDATION"


class RouteSource(str, Enum):
    RULE = "rule"
    LLM = "llm"
    FALLBACK = "fallback"


class RouteDecision(BaseModel):
    intent: Intent

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class RouteResult:
    intent: Intent
    source: RouteSource


@dataclass(frozen=True)
class RoutePlan:
    use_profile: bool
    use_history: bool
    use_rag: bool
    recommendation: bool


ROUTE_PLANS = {
    Intent.CHAT: RoutePlan(False, False, False, False),
    Intent.WORKOUT_HISTORY: RoutePlan(False, True, False, False),
    Intent.FITNESS_KNOWLEDGE: RoutePlan(False, False, True, False),
    Intent.PERSONAL_COACHING: RoutePlan(True, True, True, False),
    Intent.ROUTINE_RECOMMENDATION: RoutePlan(True, True, True, True),
}

ROUTER_SYSTEM_PROMPT = """
너는 Fit-PT 질문 분류기다. 사용자 질문을 아래 intent 중 정확히 하나로 분류한다.

- CHAT: 인사, 감사, 감정 표현, 일반 대화
- WORKOUT_HISTORY: 사용자의 과거 운동 횟수, 날짜, 중량, 거리, 페이스 등 사실 조회
- FITNESS_KNOWLEDGE: 사용자 기록과 무관한 일반 운동 원리나 방법 질문
- PERSONAL_COACHING: 사용자 프로필이나 실제 운동 기록을 바탕으로 한 분석·조언
- ROUTINE_RECOMMENDATION: 실제로 수행할 운동 루틴이나 프로그램 생성 요청

반드시 {"intent":"INTENT_NAME"} 형식의 JSON 객체 하나만 반환한다.
다른 키, 코드 블록, 설명 문장을 추가하지 않는다.
""".strip()


class IntentClassifier(Protocol):
    def classify(self, question: str) -> Intent: ...


class ProviderIntentClassifier:
    """기존 AI provider 출력을 Pydantic RouteDecision으로 검증한다."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def classify(self, question: str) -> Intent:
        raw = self.provider.generate(ROUTER_SYSTEM_PROMPT, question)
        return RouteDecision.model_validate_json(raw).intent


class QuestionRouter:
    def __init__(self, classifier: IntentClassifier) -> None:
        self.classifier = classifier

    def route(self, question: str) -> RouteResult:
        normalized = _normalize(question)
        if not normalized:
            raise ValueError("분류할 질문은 비어 있을 수 없습니다.")

        rule_intent = classify_with_rules(normalized)
        if rule_intent is not None:
            return RouteResult(rule_intent, RouteSource.RULE)

        try:
            return RouteResult(self.classifier.classify(normalized), RouteSource.LLM)
        except Exception:
            logger.warning("LLM question routing failed; falling back to CHAT", exc_info=True)
            return RouteResult(Intent.CHAT, RouteSource.FALLBACK)


def build_question_router(provider: AIProvider | None = None) -> QuestionRouter:
    return QuestionRouter(ProviderIntentClassifier(provider or get_provider()))


def get_route_plan(intent: Intent) -> RoutePlan:
    return ROUTE_PLANS[intent]


def classify_with_rules(question: str) -> Intent | None:
    """확실하게 구분할 수 있는 질문만 분류하고, 나머지는 None을 반환한다."""

    if _contains_any(question, ROUTINE_REQUEST_MARKERS):
        return Intent.ROUTINE_RECOMMENDATION

    if _contains_any(question, PERSONAL_REFERENCES) and _contains_any(
        question, COACHING_MARKERS
    ):
        return Intent.PERSONAL_COACHING

    if _is_clear_history_question(question):
        return Intent.WORKOUT_HISTORY

    if _is_clear_chat(question):
        return Intent.CHAT

    if _contains_any(question, FITNESS_TOPICS) and _contains_any(
        question, KNOWLEDGE_QUESTION_MARKERS
    ):
        return Intent.FITNESS_KNOWLEDGE

    return None


ROUTINE_REQUEST_MARKERS = (
    "루틴 짜",
    "루틴 추천",
    "운동 짜",
    "운동 추천",
    "프로그램 짜",
    "프로그램 추천",
    "운동 계획 짜",
)

PERSONAL_REFERENCES = (
    "내 최근",
    "내 기록",
    "내 운동",
    "나의 기록",
    "나의 운동",
    "제 기록",
    "제 운동",
    "기록 기준",
    "기록을 보면",
    "기록 보면",
)

COACHING_MARKERS = (
    "올려도",
    "늘려도",
    "낮춰야",
    "줄여야",
    "조절",
    "정체",
    "분석",
    "개선",
    "왜",
    "어떻게 할",
    "괜찮을",
    "적당할",
)

HISTORY_TIME_MARKERS = (
    "지난주",
    "저번주",
    "이번 주",
    "이번주",
    "지난달",
    "이번 달",
    "이번달",
    "최근",
    "지난번",
    "저번에",
)

HISTORY_DATA_MARKERS = (
    "운동",
    "기록",
    "벤치",
    "스쿼트",
    "데드",
    "중량",
    "무게",
    "러닝",
    "거리",
    "페이스",
)

HISTORY_QUERY_MARKERS = (
    "알려",
    "몇",
    "얼마",
    "했어",
    "했지",
    "뛰었",
    "어땠",
    "기록",
)

FITNESS_TOPICS = (
    "근비대",
    "점진적 과부하",
    "운동 볼륨",
    "휴식시간",
    "휴식 시간",
    "세트 간 휴식",
    "rpe",
    "rir",
    "벤치",
    "스쿼트",
    "데드리프트",
    "인터벌",
    "러닝",
    "반복 횟수",
    "운동 강도",
)

KNOWLEDGE_QUESTION_MARKERS = (
    "뭐",
    "무엇",
    "왜",
    "어떻게",
    "얼마나",
    "언제",
    "효과",
    "차이",
    "방법",
    "원리",
    "좋아",
    "해야",
    "할까",
    "인가",
    "이란",
    "?",
)

CHAT_EXACT_PHRASES = {
    "안녕",
    "안녕하세요",
    "반가워",
    "반갑습니다",
    "고마워",
    "감사해",
    "감사합니다",
    "잘 가",
}

CHAT_PHRASES = (
    "오늘 운동하기 싫",
    "운동 가기 싫",
    "너는 어떤 코치",
    "기분이 안 좋",
    "응원해줘",
)


def _normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip()).lower()


def _contains_any(question: str, markers: tuple[str, ...]) -> bool:
    return any(marker in question for marker in markers)


def _is_clear_history_question(question: str) -> bool:
    has_time_or_record = _contains_any(question, HISTORY_TIME_MARKERS) or "기록" in question
    return (
        has_time_or_record
        and _contains_any(question, HISTORY_DATA_MARKERS)
        and _contains_any(question, HISTORY_QUERY_MARKERS)
    )


def _is_clear_chat(question: str) -> bool:
    stripped = question.rstrip(".!?~ ")
    return stripped in CHAT_EXACT_PHRASES or _contains_any(question, CHAT_PHRASES)
