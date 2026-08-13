from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.routers.chat import send_message
from app.schemas.chat import ChatRequest
from app.services.ai.base import AIResult
from app.services.ai.orchestrator import OrchestrationResult, RagStatus
from app.services.ai.question_router import Intent, RouteResult, RouteSource


class FakeInsertQuery:
    def __init__(self, client: "FakeSupabase") -> None:
        self.client = client

    def insert(self, payload: dict) -> "FakeInsertQuery":
        self.client.inserted_payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=[{"id": "recommendation-1"}])


class FakeSupabase:
    def __init__(self) -> None:
        self.table_calls: list[str] = []
        self.inserted_payload: dict | None = None

    def table(self, name: str) -> FakeInsertQuery:
        self.table_calls.append(name)
        return FakeInsertQuery(self)


class FakeOrchestrator:
    def __init__(self, result: AIResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    async def run(self, user_id: str, question: str) -> OrchestrationResult:
        self.calls.append((user_id, question))
        return OrchestrationResult(
            ai_result=self.result,
            route=RouteResult(Intent.ROUTINE_RECOMMENDATION, RouteSource.RULE),
            rag_status=RagStatus.FOUND,
            rag_documents=(),
        )


class ChatOrchestrationTests(unittest.TestCase):
    def test_chat_endpoint_uses_orchestrator_and_keeps_recommendation_response(self) -> None:
        supabase = FakeSupabase()
        orchestrator = FakeOrchestrator(
            AIResult(
                response_text="오늘의 루틴입니다.",
                workout_type="weight",
                structured_data={"type": "weight", "title": "가슴 루틴"},
            )
        )

        with patch(
            "app.routers.chat.build_ai_orchestrator",
            return_value=orchestrator,
        ):
            response = asyncio.run(
                send_message(
                    ChatRequest(message="오늘 가슴 운동 짜줘"),
                    user_id="user-1",
                    supabase=supabase,
                )
            )

        self.assertEqual(orchestrator.calls, [("user-1", "오늘 가슴 운동 짜줘")])
        self.assertEqual(supabase.table_calls, ["ai_recommendations"])
        self.assertEqual(supabase.inserted_payload["user_id"], "user-1")
        self.assertEqual(
            response["recommendation"],
            {
                "id": "recommendation-1",
                "workout_type": "weight",
                "structured_data": {"type": "weight", "title": "가슴 루틴"},
            },
        )
        self.assertEqual(response["response_text"], "오늘의 루틴입니다.")
        self.assertTrue(response["message_id"])

    def test_non_recommendation_response_does_not_write_database(self) -> None:
        supabase = FakeSupabase()
        orchestrator = FakeOrchestrator(AIResult("안녕하세요!", None, None))

        with patch(
            "app.routers.chat.build_ai_orchestrator",
            return_value=orchestrator,
        ):
            response = asyncio.run(
                send_message(
                    ChatRequest(message="안녕"),
                    user_id="user-2",
                    supabase=supabase,
                )
            )

        self.assertEqual(supabase.table_calls, [])
        self.assertIsNone(response["recommendation"])
        self.assertEqual(response["response_text"], "안녕하세요!")


if __name__ == "__main__":
    unittest.main()
