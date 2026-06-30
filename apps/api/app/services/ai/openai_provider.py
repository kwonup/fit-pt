from app.core.config import settings

# openai SDK는 사용 시점에 import (미설치 provider 때문에 서버가 죽지 않도록)
_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
        from openai import OpenAI

        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


class OpenAIProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = _get_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
