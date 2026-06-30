from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.claude_provider import ClaudeProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_provider() -> AIProvider:
    provider = settings.AI_PROVIDER.lower()
    if provider == "claude":
        return ClaudeProvider()
    if provider == "openai":
        return OpenAIProvider()
    raise RuntimeError(f"알 수 없는 AI_PROVIDER: {settings.AI_PROVIDER} (openai 또는 claude)")
