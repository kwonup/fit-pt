from __future__ import annotations

import unittest

from app.services.ai.question_router import (
    Intent,
    ProviderIntentClassifier,
    QuestionRouter,
    RoutePlan,
    RouteSource,
    get_route_plan,
)


class FakeClassifier:
    def __init__(
        self,
        intent: Intent = Intent.CHAT,
        error: Exception | None = None,
    ) -> None:
        self.intent = intent
        self.error = error
        self.calls: list[str] = []

    def classify(self, question: str) -> Intent:
        self.calls.append(question)
        if self.error is not None:
            raise self.error
        return self.intent


class FakeProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


class QuestionRouterTests(unittest.TestCase):
    def test_clear_questions_use_rule_fast_path(self) -> None:
        cases = {
            "안녕": Intent.CHAT,
            "고마워": Intent.CHAT,
            "지난주 몇 번 운동했어?": Intent.WORKOUT_HISTORY,
            "최근 벤치 중량 알려줘": Intent.WORKOUT_HISTORY,
            "근비대 세트 휴식시간은?": Intent.FITNESS_KNOWLEDGE,
            "벤치 중량은 언제 올려?": Intent.FITNESS_KNOWLEDGE,
            "내 최근 벤치 기록 보면 중량 올려도 될까?": Intent.PERSONAL_COACHING,
            "최근 러닝 기록 기준으로 페이스 조절 어떻게 할까?": Intent.PERSONAL_COACHING,
            "오늘 가슴 운동 짜줘": Intent.ROUTINE_RECOMMENDATION,
            "최근 기록 기준으로 오늘 등 루틴 추천해줘": Intent.ROUTINE_RECOMMENDATION,
        }
        classifier = FakeClassifier(error=AssertionError("LLM을 호출하면 안 됩니다."))
        router = QuestionRouter(classifier)

        for question, expected in cases.items():
            with self.subTest(question=question):
                result = router.route(question)
                self.assertEqual(result.intent, expected)
                self.assertEqual(result.source, RouteSource.RULE)

        self.assertEqual(classifier.calls, [])

    def test_ambiguous_question_uses_llm_classifier(self) -> None:
        classifier = FakeClassifier(Intent.PERSONAL_COACHING)
        router = QuestionRouter(classifier)

        result = router.route("벤치프레스가 요즘 고민이야")

        self.assertEqual(result.intent, Intent.PERSONAL_COACHING)
        self.assertEqual(result.source, RouteSource.LLM)
        self.assertEqual(classifier.calls, ["벤치프레스가 요즘 고민이야"])

    def test_llm_failure_falls_back_to_chat(self) -> None:
        classifier = FakeClassifier(error=ValueError("invalid output"))
        router = QuestionRouter(classifier)

        with self.assertLogs("app.services.ai.question_router", level="WARNING"):
            result = router.route("분류하기 애매한 요청")

        self.assertEqual(result.intent, Intent.CHAT)
        self.assertEqual(result.source, RouteSource.FALLBACK)

    def test_blank_question_is_rejected_without_llm_call(self) -> None:
        classifier = FakeClassifier()
        router = QuestionRouter(classifier)

        with self.assertRaisesRegex(ValueError, "비어 있을 수 없습니다"):
            router.route("   ")

        self.assertEqual(classifier.calls, [])

    def test_provider_classifier_validates_pydantic_schema(self) -> None:
        provider = FakeProvider('{"intent":"FITNESS_KNOWLEDGE"}')
        classifier = ProviderIntentClassifier(provider)

        intent = classifier.classify("근비대란?")

        self.assertEqual(intent, Intent.FITNESS_KNOWLEDGE)
        self.assertEqual(provider.calls[0][1], "근비대란?")

    def test_provider_classifier_rejects_extra_fields(self) -> None:
        provider = FakeProvider('{"intent":"CHAT","reason":"인사"}')
        classifier = ProviderIntentClassifier(provider)

        with self.assertRaises(ValueError):
            classifier.classify("안녕인지 애매한 문장")

    def test_route_plans_select_only_required_resources(self) -> None:
        self.assertEqual(
            get_route_plan(Intent.CHAT),
            RoutePlan(False, False, False, False),
        )
        self.assertEqual(
            get_route_plan(Intent.WORKOUT_HISTORY),
            RoutePlan(False, True, False, False),
        )
        self.assertEqual(
            get_route_plan(Intent.FITNESS_KNOWLEDGE),
            RoutePlan(False, False, True, False),
        )
        self.assertEqual(
            get_route_plan(Intent.PERSONAL_COACHING),
            RoutePlan(True, True, True, False),
        )
        self.assertEqual(
            get_route_plan(Intent.ROUTINE_RECOMMENDATION),
            RoutePlan(True, True, True, True),
        )


if __name__ == "__main__":
    unittest.main()
