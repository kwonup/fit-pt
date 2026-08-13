import unittest

from langchain_core.prompts import ChatPromptTemplate

from app.services.ai.prompts import AI_PROMPT_TEMPLATE, build_ai_prompt
from app.services.ai.question_router import Intent


class AIPromptTests(unittest.TestCase):
    def test_uses_langchain_chat_prompt_template(self) -> None:
        self.assertIsInstance(AI_PROMPT_TEMPLATE, ChatPromptTemplate)

    def test_non_recommendation_intent_requires_null_card(self) -> None:
        prompt = build_ai_prompt(
            persona="angel",
            intent=Intent.WORKOUT_HISTORY,
            context="최근 30일 운동: 총 3회",
            question="지난달에 몇 번 운동했어?",
        )

        self.assertIn("있는 기록만 근거로", prompt.system_prompt)
        self.assertIn('"is_recommendation": false', prompt.system_prompt)
        self.assertIn('"structured_data": null', prompt.system_prompt)
        self.assertNotIn("structured_data JSON Schema", prompt.system_prompt)

    def test_knowledge_intent_requires_numbered_citations(self) -> None:
        prompt = build_ai_prompt(
            persona="angel",
            intent=Intent.FITNESS_KNOWLEDGE,
            context="[자료 1]\n제목: 근비대 논문",
            question="근비대 반복수는 몇 회가 좋아?",
        )

        self.assertIn("[자료 1]처럼 자료 번호", prompt.system_prompt)
        self.assertIn("출처를 지어내지", prompt.system_prompt)
        self.assertIn("제목: 근비대 논문", prompt.user_prompt)

    def test_routine_intent_contains_card_schema_and_persona(self) -> None:
        prompt = build_ai_prompt(
            persona="tiger",
            intent=Intent.ROUTINE_RECOMMENDATION,
            context="숙련도: 중급",
            question="오늘 등 루틴 짜줘",
        )

        self.assertIn("엄격한 호랑이 코치", prompt.system_prompt)
        self.assertIn("structured_data JSON Schema", prompt.system_prompt)
        self.assertIn('"maxItems":8', prompt.system_prompt)
        self.assertIn('"estimated_duration_minutes"', prompt.system_prompt)
        self.assertIn("오늘 등 루틴 짜줘", prompt.user_prompt)

    def test_inserted_context_is_data_not_a_template(self) -> None:
        prompt = build_ai_prompt(
            persona="unknown",
            intent=Intent.CHAT,
            context='사용자 메모: {"주의": "허리"}',
            question="안녕 {코치}",
        )

        self.assertIn("상냥한 천사 코치", prompt.system_prompt)
        self.assertIn('{"주의": "허리"}', prompt.user_prompt)
        self.assertIn("안녕 {코치}", prompt.user_prompt)


if __name__ == "__main__":
    unittest.main()
