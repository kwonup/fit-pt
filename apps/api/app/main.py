from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import profile, workouts, chat, stats

app = FastAPI(
    title="Fit PT API",
    description="핏피티 AI 코칭 운동 기록 서비스 백엔드",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
