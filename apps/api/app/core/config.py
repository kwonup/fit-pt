from typing import Literal

from pydantic import Field
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

    # 전문지식 RAG embedding 규격. DB vector(1536)과 함께 변경해야 한다.
    EMBEDDING_PROVIDER: Literal["openai"] = "openai"
    OPENAI_EMBEDDING_MODEL: Literal["text-embedding-3-small"] = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: Literal[1536] = 1536
    RAG_TOP_K: int = Field(default=4, ge=1, le=20)
    RAG_MATCH_THRESHOLD: float = Field(default=0.70, ge=0.0, le=1.0)

    FRONTEND_ORIGIN: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
