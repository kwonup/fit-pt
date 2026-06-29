from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    OPENAI_API_KEY: str
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
