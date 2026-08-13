from __future__ import annotations

import json
import unittest

from app.services.ai.parser import parse_ai_response


def recommendation_response(structured_data: dict, workout_type: str | None = None) -> str:
    return json.dumps(
        {
            "response_text": "추천 이유와 주의사항입니다.",
            "is_recommendation": True,
            "workout_type": workout_type or structured_data.get("type"),
            "structured_data": structured_data,
        },
        ensure_ascii=False,
    )


def valid_weight_recommendation() -> dict:
    return {
        "type": "weight",
        "title": "오늘의 등 루틴",
        "estimated_duration_minutes": 50,
        "muscle_group": "등",
        "exercises": [
            {
                "name": "랫풀다운",
                "sets": [
                    {
                        "set_number": 1,
                        "weight_kg": 40,
                        "reps": 12,
                        "rest_seconds": 90,
                    }
                ],
                "notes": "허리 중립 유지",
            }
        ],
        "cautions": "통증이 생기면 중단",
    }


class RecommendationSchemaTests(unittest.TestCase):
    def test_valid_weight_recommendation_keeps_card(self) -> None:
        result = parse_ai_response(recommendation_response(valid_weight_recommendation()))

        self.assertEqual(result.workout_type, "weight")
        self.assertEqual(result.structured_data["muscle_group"], "등")
        self.assertEqual(result.structured_data["exercises"][0]["sets"][0]["reps"], 12)

    def test_missing_required_weight_field_discards_card(self) -> None:
        recommendation = valid_weight_recommendation()
        recommendation.pop("estimated_duration_minutes")

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertIsNone(result.workout_type)
        self.assertIsNone(result.structured_data)
        self.assertEqual(result.response_text, "추천 이유와 주의사항입니다.")

    def test_more_than_eight_weight_exercises_discards_card(self) -> None:
        recommendation = valid_weight_recommendation()
        recommendation["exercises"] = recommendation["exercises"] * 9

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertIsNone(result.workout_type)
        self.assertIsNone(result.structured_data)

    def test_unexpected_recommendation_field_discards_card(self) -> None:
        recommendation = valid_weight_recommendation()
        recommendation["unsafe_extra"] = "프론트 계약에 없는 값"

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertIsNone(result.workout_type)
        self.assertIsNone(result.structured_data)

    def test_valid_running_recommendation_keeps_card(self) -> None:
        recommendation = {
            "type": "running",
            "title": "회복 러닝",
            "total_duration_minutes": 30,
            "distance_km": 4.0,
            "avg_pace": "7:30",
            "warmup": "5분 걷기",
            "main": "20분 편안한 러닝",
            "cooldown": "5분 걷기",
            "cautions": "무릎 통증 시 중단",
        }

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertEqual(result.workout_type, "running")
        self.assertEqual(result.structured_data["avg_pace"], "7:30")

    def test_invalid_running_pace_discards_card(self) -> None:
        recommendation = {
            "type": "running",
            "title": "회복 러닝",
            "total_duration_minutes": 30,
            "distance_km": 4.0,
            "avg_pace": "천천히",
            "warmup": "5분 걷기",
            "main": "20분 편안한 러닝",
            "cooldown": "5분 걷기",
            "cautions": "",
        }

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertIsNone(result.structured_data)

    def test_valid_other_recommendation_omits_null_optional_fields(self) -> None:
        recommendation = {
            "type": "other",
            "title": "회복 스트레칭",
            "content": "고관절 가동성 운동 10분",
            "estimated_duration_minutes": None,
            "cautions": None,
        }

        result = parse_ai_response(recommendation_response(recommendation))

        self.assertEqual(result.workout_type, "other")
        self.assertEqual(
            result.structured_data,
            {
                "type": "other",
                "title": "회복 스트레칭",
                "content": "고관절 가동성 운동 10분",
            },
        )


if __name__ == "__main__":
    unittest.main()
