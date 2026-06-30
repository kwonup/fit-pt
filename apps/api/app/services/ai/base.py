from dataclasses import dataclass
from typing import Protocol


@dataclass
class AIResult:
    response_text: str
    workout_type: str | None
    structured_data: dict | None


class AIProvider(Protocol):
    # 시스템/사용자 프롬프트를 받아 AI의 원시 JSON 문자열을 반환한다.
    # 파싱은 services/ai/parser.py가 담당한다.
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
