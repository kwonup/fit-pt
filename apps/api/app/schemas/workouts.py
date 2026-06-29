from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


MuscleGroup = Literal["가슴", "등", "어깨", "팔", "하체", "코어", "전신"]
Intensity = Literal["낮음", "보통", "높음"]


class WeightSetCreate(BaseModel):
    set_number: int = Field(ge=1)
    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)


class WeightExerciseCreate(BaseModel):
    exercise_name: str = Field(min_length=1, max_length=100)
    order_index: int = Field(default=0, ge=0)
    sets: list[WeightSetCreate] = Field(default_factory=list)


class WeightWorkoutCreate(BaseModel):
    workout_date: date
    title: str = Field(min_length=1, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1)
    memo: str | None = None
    ai_recommendation_id: str | None = None
    exercises: list[WeightExerciseCreate] = Field(min_length=1)


class RunningWorkoutCreate(BaseModel):
    workout_date: date
    title: str = Field(min_length=1, max_length=100)
    distance_km: float = Field(gt=0)
    duration_minutes: int = Field(ge=1)
    avg_pace: str | None = None
    intensity: Intensity | None = None
    memo: str | None = None
    ai_recommendation_id: str | None = None

    @model_validator(mode="after")
    def fill_avg_pace(self) -> "RunningWorkoutCreate":
        if self.avg_pace is None and self.distance_km > 0:
            total_seconds = round((self.duration_minutes * 60) / self.distance_km)
            minutes, seconds = divmod(total_seconds, 60)
            self.avg_pace = f"{minutes}:{seconds:02d}"
        return self


class OtherWorkoutCreate(BaseModel):
    workout_date: date
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    duration_minutes: int | None = Field(default=None, ge=1)
    memo: str | None = None
    ai_recommendation_id: str | None = None


class WorkoutSessionUpdate(BaseModel):
    workout_date: date | None = None
    title: str | None = Field(default=None, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1)
    memo: str | None = None
