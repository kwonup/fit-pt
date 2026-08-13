from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any

from langchain_core.documents import Document

from app.services.ai.orchestrator import AIOrchestrator, RagStatus
from app.services.ai.question_router import (
    Intent,
    ProviderIntentClassifier,
    QuestionRouter,
    RouteSource,
)
from app.services.context import WorkoutContext


NON_RECOMMENDATION_RESPONSE = json.dumps(
    {
        "response_text": "확인한 내용을 알려드릴게요.",
        "is_recommendation": False,
        "workout_type": None,
        "structured_data": None,
    },
    ensure_ascii=False,
)


class ScriptedAIProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if not self.responses:
            raise AssertionError("준비된 AI 응답을 모두 사용했습니다.")
        return self.responses.pop(0)


class RecordingContextProvider:
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
        return WorkoutContext(
            profile={"persona": "angel"} if use_profile else None,
            profile_context="- 운동 목표: 근성장" if use_profile else None,
            history_context="- 최근 벤치프레스: 60kg 10회" if use_history else None,
        )


class RecordingRetriever:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    async def ainvoke(self, question: str) -> list[Document]:
        self.calls.append(question)
        return self.documents


def knowledge_document() -> Document:
    return Document(
        page_content=(
            "40%, 60%, 80% 1RM 사이에서 동화 관련 호르몬의 유의한 차이는 없었다."
        ),
        metadata={
            "title": "저항운동 강도에 따른 호르몬 및 대사 반응",
            "source_name": "고려대학교 대학원 체육학과",
            "similarity": 0.54,
        },
    )


def build_orchestrator(
    provider: ScriptedAIProvider,
    context_provider: RecordingContextProvider,
    retriever: RecordingRetriever,
) -> AIOrchestrator:
    return AIOrchestrator(
        router=QuestionRouter(ProviderIntentClassifier(provider)),
        context_provider=context_provider,
        retriever_factory=lambda: retriever,
        ai_provider=provider,
    )


class AIRagIntegrationTests(unittest.TestCase):
    def test_semantic_knowledge_question_routes_to_rag_and_cites_document(self) -> None:
        question = "40%, 60%, 80% 1RM 중 어떤 강도가 호르몬 반응이 좋아?"
        provider = ScriptedAIProvider(
            [
                '```json\n{"intent":"FITNESS_KNOWLEDGE"}\n```',
                json.dumps(
                    {
                        "response_text": "세 강도 사이에 유의한 차이는 없었습니다. [자료 1]",
                        "is_recommendation": False,
                        "workout_type": None,
                        "structured_data": None,
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        context_provider = RecordingContextProvider()
        retriever = RecordingRetriever([knowledge_document()])
        orchestrator = build_orchestrator(provider, context_provider, retriever)

        result = asyncio.run(orchestrator.run("user-1", question))

        self.assertEqual(result.route.intent, Intent.FITNESS_KNOWLEDGE)
        self.assertEqual(result.route.source, RouteSource.LLM)
        self.assertEqual(result.rag_status, RagStatus.FOUND)
        self.assertEqual(context_provider.calls, [])
        self.assertEqual(retriever.calls, [question])
        self.assertEqual(len(provider.calls), 2)
        answer_system, answer_user = provider.calls[1]
        self.assertIn("[자료 1]처럼 자료 번호", answer_system)
        self.assertIn("저항운동 강도에 따른 호르몬 및 대사 반응", answer_user)
        self.assertIn("유의한 차이는 없었다", answer_user)
        self.assertIn("[자료 1]", result.ai_result.response_text)
        self.assertIsNone(result.ai_result.structured_data)

    def test_history_question_uses_sql_context_without_rag(self) -> None:
        question = "최근 벤치 중량 알려줘"
        provider = ScriptedAIProvider([NON_RECOMMENDATION_RESPONSE])
        context_provider = RecordingContextProvider()
        retriever = RecordingRetriever([knowledge_document()])
        orchestrator = build_orchestrator(provider, context_provider, retriever)

        result = asyncio.run(orchestrator.run("user-2", question))

        self.assertEqual(result.route.intent, Intent.WORKOUT_HISTORY)
        self.assertEqual(result.route.source, RouteSource.RULE)
        self.assertEqual(result.rag_status, RagStatus.NOT_USED)
        self.assertEqual(retriever.calls, [])
        self.assertEqual(
            context_provider.calls,
            [
                {
                    "user_id": "user-2",
                    "message": question,
                    "use_profile": False,
                    "use_history": True,
                }
            ],
        )
        self.assertIn("최근 벤치프레스: 60kg 10회", provider.calls[0][1])
        self.assertNotIn("검색된 운동 전문지식", provider.calls[0][1])

    def test_routine_question_combines_all_context_and_returns_valid_card(self) -> None:
        question = "최근 기록 기준으로 오늘 가슴 루틴 추천해줘"
        recommendation = json.dumps(
            {
                "response_text": "최근 기록과 전문 자료를 반영했습니다. [자료 1]",
                "is_recommendation": True,
                "workout_type": "weight",
                "structured_data": {
                    "type": "weight",
                    "title": "오늘의 가슴 루틴",
                    "estimated_duration_minutes": 45,
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
                            "notes": "통제된 동작으로 수행",
                        }
                    ],
                    "cautions": "통증이 생기면 중단",
                },
            },
            ensure_ascii=False,
        )
        provider = ScriptedAIProvider([recommendation])
        context_provider = RecordingContextProvider()
        retriever = RecordingRetriever([knowledge_document()])
        orchestrator = build_orchestrator(provider, context_provider, retriever)

        result = asyncio.run(orchestrator.run("user-3", question))

        self.assertEqual(result.route.intent, Intent.ROUTINE_RECOMMENDATION)
        self.assertEqual(result.route.source, RouteSource.RULE)
        self.assertEqual(result.rag_status, RagStatus.FOUND)
        self.assertEqual(retriever.calls, [question])
        self.assertTrue(context_provider.calls[0]["use_profile"])
        self.assertTrue(context_provider.calls[0]["use_history"])
        self.assertIn("운동 목표: 근성장", provider.calls[0][1])
        self.assertIn("최근 벤치프레스: 60kg 10회", provider.calls[0][1])
        self.assertIn("검색된 운동 전문지식", provider.calls[0][1])
        self.assertEqual(result.ai_result.workout_type, "weight")
        self.assertEqual(result.ai_result.structured_data["muscle_group"], "가슴")


if __name__ == "__main__":
    unittest.main()
