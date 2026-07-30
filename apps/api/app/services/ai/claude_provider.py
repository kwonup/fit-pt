from app.core.config import settings

# anthropic SDK는 사용 시점에 import (미설치 provider 때문에 서버가 죽지 않도록)
_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


class ClaudeProvider:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = _get_client()
        # Claude는 JSON 모드가 없으므로 시스템 프롬프트의 "JSON만 반환" 지시에 의존한다.
        request_options = {
            "model": settings.CLAUDE_MODEL,
            "max_tokens": settings.AI_MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        # Haiku 4.5는 effort/adaptive thinking을 지원하지 않는다.
        if "haiku" not in settings.CLAUDE_MODEL.lower():
            request_options["thinking"] = {
                "type": "adaptive" if settings.CLAUDE_THINKING_ENABLED else "disabled"
            }
            request_options["output_config"] = {"effort": settings.CLAUDE_EFFORT}

        message = client.messages.create(**request_options)
        for block in message.content:
            if block.type == "text":
                return block.text
        return ""
