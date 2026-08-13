from __future__ import annotations

import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.services.context import WorkoutContextProvider, build_user_context


@dataclass
class QueryCall:
    table: str
    operations: list[tuple[str, tuple[Any, ...]]]


class FakeQuery:
    def __init__(self, client: "FakeSupabase", table: str) -> None:
        self.client = client
        self.table_name = table
        self.operations: list[tuple[str, tuple[Any, ...]]] = []

    def _record(self, name: str, *args: Any) -> "FakeQuery":
        self.operations.append((name, args))
        return self

    def select(self, columns: str) -> "FakeQuery":
        return self._record("select", columns)

    def eq(self, column: str, value: Any) -> "FakeQuery":
        return self._record("eq", column, value)

    def gte(self, column: str, value: Any) -> "FakeQuery":
        return self._record("gte", column, value)

    def order(self, column: str, *, desc: bool = False) -> "FakeQuery":
        return self._record("order", column, desc)

    def limit(self, count: int) -> "FakeQuery":
        return self._record("limit", count)

    def execute(self) -> SimpleNamespace:
        self.client.query_calls.append(QueryCall(self.table_name, self.operations.copy()))
        return SimpleNamespace(data=self.client.table_rows.get(self.table_name, []))


class FakeRpcQuery:
    def __init__(self, client: "FakeSupabase", name: str, params: dict[str, Any]) -> None:
        self.client = client
        self.name = name
        self.params = params

    def execute(self) -> SimpleNamespace:
        self.client.rpc_calls.append((self.name, self.params))
        return SimpleNamespace(data=self.client.rpc_rows.get(self.name, []))


class FakeSupabase:
    def __init__(
        self,
        *,
        table_rows: dict[str, list[dict[str, Any]]] | None = None,
        rpc_rows: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.table_rows = table_rows or {}
        self.rpc_rows = rpc_rows or {}
        self.query_calls: list[QueryCall] = []
        self.rpc_calls: list[tuple[str, dict[str, Any]]] = []

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> FakeRpcQuery:
        return FakeRpcQuery(self, name, params)


class WorkoutContextProviderTests(unittest.TestCase):
    def test_profile_only_fetches_whitelisted_profile_for_user(self) -> None:
        client = FakeSupabase(
            table_rows={
                "user_profiles": [
                    {
                        "fitness_goals": ["근비대"],
                        "fitness_level": "중급",
                        "main_workout_type": "웨이트트레이닝",
                        "weekly_frequency": 4,
                        "caution_areas": ["허리"],
                        "persona": "angel",
                    }
                ]
            }
        )

        context = WorkoutContextProvider(client).load(
            "user-1",
            use_profile=True,
            use_history=False,
        )

        self.assertEqual(context.profile["persona"], "angel")
        self.assertIn("- 운동 목표: 근비대", context.to_prompt())
        self.assertIn("- 주의/부상 부위: 허리", context.to_prompt())
        self.assertIsNone(context.history_context)
        self.assertEqual([call.table for call in client.query_calls], ["user_profiles"])
        self.assertIn(("eq", ("id", "user-1")), client.query_calls[0].operations)
        selected_columns = client.query_calls[0].operations[0][1][0]
        self.assertNotIn("id", selected_columns.split(", "))
        self.assertEqual(client.rpc_calls, [])

    def test_history_only_uses_user_scoped_sql_and_rpc(self) -> None:
        client = FakeSupabase(
            table_rows={
                "workout_sessions": [
                    {
                        "workout_date": "2026-08-12",
                        "workout_type": "weight",
                        "title": "가슴 운동",
                        "duration_minutes": 50,
                        "memo": "마지막 세트에서 오른쪽 어깨가 약간 불편했음",
                        "running_sessions": None,
                    },
                    {
                        "workout_date": "2026-08-10",
                        "workout_type": "running",
                        "title": "저녁 러닝",
                        "duration_minutes": 30,
                        "memo": None,
                        "running_sessions": {
                            "distance_km": 5.2,
                            "avg_pace": "5:46",
                            "intensity": "보통",
                        },
                    },
                ]
            },
            rpc_rows={
                "get_weight_exercise_maxes": [
                    {
                        "exercise_name": "벤치프레스",
                        "best_weight_kg": 80,
                        "best_reps": 5,
                        "recent_weight_kg": 77.5,
                        "recent_reps": 6,
                    }
                ]
            },
        )

        context = WorkoutContextProvider(client).load(
            "user-2",
            use_profile=False,
            use_history=True,
        )

        prompt = context.to_prompt()
        self.assertIsNone(context.profile_context)
        self.assertIn("최근 30일 운동: 총 2회", prompt)
        self.assertIn("웨이트 1회", prompt)
        self.assertIn("러닝 1회", prompt)
        self.assertIn("벤치프레스(최고 80kg×5, 최근 77.5kg×6)", prompt)
        self.assertIn("메모: 마지막 세트에서 오른쪽 어깨가 약간 불편했음", prompt)
        self.assertIn("5.2km 평균 페이스 5:46/km 강도 보통", prompt)
        self.assertEqual([call.table for call in client.query_calls], ["workout_sessions"])
        self.assertIn(("eq", ("user_id", "user-2")), client.query_calls[0].operations)
        self.assertEqual(
            client.rpc_calls,
            [("get_weight_exercise_maxes", {"p_user_id": "user-2"})],
        )

    def test_question_specific_weight_detail_queries_remain_user_scoped(self) -> None:
        client = FakeSupabase(
            table_rows={
                "workout_sessions": [
                    {
                        "workout_date": "2026-08-12",
                        "workout_type": "weight",
                        "title": "가슴 운동",
                        "duration_minutes": 50,
                        "memo": None,
                        "running_sessions": None,
                        "weight_exercises": [
                            {
                                "exercise_name": "벤치프레스",
                                "weight_sets": [
                                    {"set_number": 1, "weight_kg": 70, "reps": 8}
                                ],
                            }
                        ],
                    }
                ]
            }
        )

        context = WorkoutContextProvider(client).load(
            "user-5",
            "내 최근 벤치 기록 알려줘",
            use_profile=False,
            use_history=True,
        )

        workout_queries = [
            call for call in client.query_calls if call.table == "workout_sessions"
        ]
        self.assertGreaterEqual(len(workout_queries), 2)
        for query in workout_queries:
            self.assertIn(("eq", ("user_id", "user-5")), query.operations)
        self.assertIn("벤치프레스: 70kg×8", context.to_prompt())

    def test_recent_memo_is_compacted_and_length_limited(self) -> None:
        long_memo = "  무릎 상태를 확인함  " * 40
        client = FakeSupabase(
            table_rows={
                "workout_sessions": [
                    {
                        "workout_date": "2026-08-12",
                        "workout_type": "weight",
                        "title": "하체 운동",
                        "duration_minutes": 40,
                        "memo": long_memo,
                        "running_sessions": None,
                    }
                ]
            }
        )

        context = WorkoutContextProvider(client).load(
            "user-6",
            use_profile=False,
            use_history=True,
        )

        memo_text = context.to_prompt().split("메모: ", maxsplit=1)[1].split("\n", maxsplit=1)[0]
        self.assertTrue(memo_text.endswith("…"))
        self.assertLessEqual(len(memo_text), 201)
        self.assertNotIn("  ", memo_text)

    def test_unrequested_resources_do_not_query_database(self) -> None:
        client = FakeSupabase()

        context = WorkoutContextProvider(client).load(
            "user-3",
            use_profile=False,
            use_history=False,
        )

        self.assertEqual(context.to_prompt(), "")
        self.assertEqual(client.query_calls, [])
        self.assertEqual(client.rpc_calls, [])

    def test_missing_profile_and_history_have_safe_fallback_text(self) -> None:
        client = FakeSupabase()

        context = WorkoutContextProvider(client).load(
            "new-user",
            use_profile=True,
            use_history=True,
        )

        self.assertIn("프로필 미설정", context.to_prompt())
        self.assertIn("최근 30일 운동 기록 없음", context.to_prompt())

    def test_blank_user_id_is_rejected_before_queries(self) -> None:
        client = FakeSupabase()

        with self.assertRaisesRegex(ValueError, "user_id"):
            WorkoutContextProvider(client).load(
                "   ",
                use_profile=True,
                use_history=True,
            )

        self.assertEqual(client.query_calls, [])

    def test_legacy_context_builder_keeps_combined_contract(self) -> None:
        client = FakeSupabase()
        profile = {
            "fitness_goals": ["체력 향상"],
            "fitness_level": "초보",
            "main_workout_type": "둘다",
            "weekly_frequency": 3,
            "caution_areas": [],
        }

        prompt = build_user_context(client, "user-4", profile)

        self.assertIn("- 운동 목표: 체력 향상", prompt)
        self.assertIn("- 최근 30일 운동 기록 없음", prompt)


if __name__ == "__main__":
    unittest.main()
