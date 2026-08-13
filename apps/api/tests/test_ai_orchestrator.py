from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any

from langchain_core.documents import Document

from app.services.ai.orchestrator import AIOrchestrator, RagStatus
from app.services.ai.question_router import Intent, RouteResult, RouteSource
from app.services.context import WorkoutContext


NON_RECOMMENDATION_RESPONSE = (
    '{"response_text":"답변입니다.","is_recommendation":false,'
    '"workout_type":null,"structured_data":null}'
)

WEIGHT_RECOMMENDATION_RESPONSE = json.dumps(
    {
        "response_text": "루틴입니다.",
        "is_recommendation": True,
        "workout_type": "weight",
        "structured_data": {
            "type": "weight",
            "title": "가슴 루틴",
            "estimated_duration_minutes": 50,
            "muscle_group": "가슴",
            "exercises": [
                {
                    "name": "벤치프레스",
                    "sets": [
                        {
                            "set_number": 1,
                            "weight_kg": 60,
                            "reps": 10,
                            "rest_seconds": 90,
                        }
                    ],
                    "notes": "견갑을 고정하세요.",
                }
            ],
            "cautions": "어깨 통증이 생기면 중단하세요.",
        },
    },
    ensure_ascii=False,
)


class FakeRouter:
    def __init__(self, intent: Intent) -> None:
        self.intent = intent
        self.calls: list[str] = []

    def route(self, question: str) -> RouteResult:
        self.calls.append(question)
        return RouteResult(self.intent, RouteSource.RULE)


class FakeContextProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def load(
        self,
        user_id: str,
        message: str,
        *,
        use_profile: bool,
        use_history: bool,
    ) -> WorkoutContext:
        self.calls.append(
            {
                "user_id": user_id,
                "message": message,
                "use_profile": use_profile,
                "use_history": use_history,
            }
        )
        profile = {"persona": "tiger"} if use_profile else None
        return WorkoutContext(
            profile=profile,
            profile_context="- 숙련도: 중급" if use_profile else None,
            history_context="- 최근 30일 운동: 총 3회" if use_history else None,
        )


class FakeRetriever:
    def __init__(
        self,
        documents: list[Document] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.documents = documents or []
        self.error = error
        self.calls: list[str] = []

    async def ainvoke(self, question: str) -> list[Document]:
        self.calls.append(question)
        if self.error is not None:
            raise self.error
        return self.documents


class FakeRetrieverFactory:
    def __init__(self, retriever: FakeRetriever) -> None:
        self.retriever = retriever
        self.call_count = 0

    def __call__(self) -> FakeRetriever:
        self.call_count += 1
        return self.retriever


class FakeAIProvider:
    def __init__(self, response: str = NON_RECOMMENDATION_RESPONSE) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def sample_document() -> Document:
    return Document(
        page_content="근비대는 다양한 부하 범위에서 일어날 수 있습니다.",
        metadata={
            "title": "ACSM 저항운동 가이드",
            "source_name": "ACSM",
            "source_url": "https://example.org/paper",
            "page": 3,
            "similarity": 0.82,
        },
    )


class AIOrchestratorTests(unittest.TestCase):
    def _run_for_intent(
        self,
        intent: Intent,
        *,
        provider_response: str = NON_RECOMMENDATION_RESPONSE,
        documents: list[Document] | None = None,
        retrieval_error: Exception | None = None,
    ) -> tuple[Any, FakeContextProvider, FakeRetrieverFactory, FakeAIProvider]:
        context_provider = FakeContextProvider()
        retriever = FakeRetriever(documents, retrieval_error)
        factory = FakeRetrieverFactory(retriever)
        provider = FakeAIProvider(provider_response)
        orchestrator = AIOrchestrator(
            router=FakeRouter(intent),
            context_provider=context_provider,
            retriever_factory=factory,
            ai_provider=provider,
        )

        result = asyncio.run(orchestrator.run("user-1", "테스트 질문"))
        return result, context_provider, factory, provider

    def test_each_intent_loads_only_planned_resources(self) -> None:
        cases = {
            Intent.CHAT: (False, False, False),
            Intent.WORKOUT_HISTORY: (False, True, False),
            Intent.FITNESS_KNOWLEDGE: (False, False, True),
            Intent.PERSONAL_COACHING: (True, True, True),
            Intent.ROUTINE_RECOMMENDATION: (True, True, True),
        }

        for intent, (use_profile, use_history, use_rag) in cases.items():
            with self.subTest(intent=intent):
                result, context_provider, factory, provider = self._run_for_intent(
                    intent,
                    documents=[sample_document()],
                )

                if use_profile or use_history:
                    self.assertEqual(len(context_provider.calls), 1)
                    self.assertEqual(
                        context_provider.calls[0]["use_profile"],
                        use_profile,
                    )
                    self.assertEqual(
                        context_provider.calls[0]["use_history"],
                        use_history,
                    )
                    self.assertEqual(context_provider.calls[0]["user_id"], "user-1")
                else:
                    self.assertEqual(context_provider.calls, [])

                self.assertEqual(factory.call_count, int(use_rag))
                self.assertEqual(
                    result.rag_status,
                    RagStatus.FOUND if use_rag else RagStatus.NOT_USED,
                )
                self.assertEqual(len(provider.calls), 1)
                self.assertIn(intent.value, provider.calls[0][1])

    def test_prompt_contains_only_selected_context_and_rag_provenance(self) -> None:
        _, _, _, history_provider = self._run_for_intent(Intent.WORKOUT_HISTORY)
        history_prompt = history_provider.calls[0][1]
        self.assertIn("최근 30일 운동: 총 3회", history_prompt)
        self.assertNotIn("검색된 운동 전문지식", history_prompt)
        self.assertNotIn("숙련도: 중급", history_prompt)

        _, _, _, knowledge_provider = self._run_for_intent(
            Intent.FITNESS_KNOWLEDGE,
            documents=[sample_document()],
        )
        knowledge_prompt = knowledge_provider.calls[0][1]
        self.assertIn("[검색된 운동 전문지식]", knowledge_prompt)
        self.assertIn("제목: ACSM 저항운동 가이드", knowledge_prompt)
        self.assertIn("출처: ACSM", knowledge_prompt)
        self.assertIn("페이지: 3", knowledge_prompt)
        self.assertIn("근비대는 다양한 부하 범위", knowledge_prompt)
        self.assertNotIn("최근 30일 운동", knowledge_prompt)

        _, _, _, coaching_provider = self._run_for_intent(
            Intent.PERSONAL_COACHING,
            documents=[sample_document()],
        )
        coaching_system, coaching_prompt = coaching_provider.calls[0]
        self.assertIn("숙련도: 중급", coaching_prompt)
        self.assertIn("최근 30일 운동: 총 3회", coaching_prompt)
        self.assertIn("검색된 운동 전문지식", coaching_prompt)
        self.assertIn("엄격한 호랑이 코치", coaching_system)

    def test_rag_failure_continues_without_fabricated_search_context(self) -> None:
        with self.assertLogs("app.services.ai.orchestrator", level="WARNING"):
            result, _, factory, provider = self._run_for_intent(
                Intent.FITNESS_KNOWLEDGE,
                retrieval_error=RuntimeError("vector database unavailable"),
            )

        self.assertEqual(result.rag_status, RagStatus.UNAVAILABLE)
        self.assertEqual(result.rag_documents, ())
        self.assertEqual(factory.call_count, 1)
        self.assertIn("검색 시스템을 현재 사용할 수 없습니다", provider.calls[0][1])
        self.assertIn("인용한 것처럼 답하지 마세요", provider.calls[0][1])
        self.assertEqual(result.ai_result.response_text, "답변입니다.")

    def test_empty_rag_result_is_distinguished_from_failure(self) -> None:
        result, _, _, provider = self._run_for_intent(Intent.FITNESS_KNOWLEDGE)

        self.assertEqual(result.rag_status, RagStatus.EMPTY)
        self.assertIn("관련성이 충분한 자료를 찾지 못했습니다", provider.calls[0][1])

    def test_non_recommendation_route_discards_unexpected_card_data(self) -> None:
        result, _, _, _ = self._run_for_intent(
            Intent.FITNESS_KNOWLEDGE,
            provider_response=WEIGHT_RECOMMENDATION_RESPONSE,
            documents=[sample_document()],
        )

        self.assertEqual(result.ai_result.response_text, "루틴입니다.")
        self.assertIsNone(result.ai_result.workout_type)
        self.assertIsNone(result.ai_result.structured_data)

    def test_recommendation_route_preserves_existing_card_contract(self) -> None:
        result, _, _, _ = self._run_for_intent(
            Intent.ROUTINE_RECOMMENDATION,
            provider_response=WEIGHT_RECOMMENDATION_RESPONSE,
            documents=[sample_document()],
        )

        self.assertEqual(result.ai_result.workout_type, "weight")
        self.assertEqual(result.ai_result.structured_data["title"], "가슴 루틴")


if __name__ == "__main__":
    unittest.main()
