from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # AI provider 선택: "openai" 또는 "claude"
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_EFFORT: Literal["low", "medium", "high"] = "medium"
    CLAUDE_THINKING_ENABLED: bool = False
    AI_MAX_TOKENS: int = 4096

    FRONTEND_ORIGIN: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
