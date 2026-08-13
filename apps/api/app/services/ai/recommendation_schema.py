from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.schemas.workouts import MuscleGroup


class RecommendationModel(BaseModel):
    """웹 추천 카드로 전달할 수 있는 데이터만 허용하는 공통 모델."""

    model_config = ConfigDict(extra="forbid")


class RecommendedWeightSet(RecommendationModel):
    set_number: int = Field(ge=1)
    weight_kg: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    rest_seconds: int | None = Field(default=None, ge=0)


class RecommendedWeightExercise(RecommendationModel):
    name: str = Field(min_length=1, max_length=100)
    sets: list[RecommendedWeightSet] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=500)


class WeightRecommendation(RecommendationModel):
    type: Literal["weight"]
    title: str = Field(min_length=1, max_length=100)
    estimated_duration_minutes: int = Field(ge=1)
    muscle_group: MuscleGroup
    exercises: list[RecommendedWeightExercise] = Field(min_length=1, max_length=8)
    cautions: str = Field(max_length=1000)


class RunningRecommendation(RecommendationModel):
    type: Literal["running"]
    title: str = Field(min_length=1, max_length=100)
    total_duration_minutes: int = Field(ge=1)
    distance_km: float = Field(gt=0)
    avg_pace: str = Field(pattern=r"^\d{1,2}:\d{2}$")
    warmup: str = Field(min_length=1, max_length=1000)
    main: str = Field(min_length=1, max_length=2000)
    cooldown: str = Field(min_length=1, max_length=1000)
    cautions: str = Field(max_length=1000)


class OtherRecommendation(RecommendationModel):
    type: Literal["other"]
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=5000)
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    cautions: str | None = Field(default=None, max_length=1000)


Recommendation = Annotated[
    WeightRecommendation | RunningRecommendation | OtherRecommendation,
    Field(discriminator="type"),
]

_RECOMMENDATION_ADAPTER = TypeAdapter(Recommendation)


def validate_recommendation(data: object) -> dict:
    """추천 데이터를 검증하고 JSON으로 안전하게 직렬화할 수 있는 dict로 정규화한다."""

    recommendation = _RECOMMENDATION_ADAPTER.validate_python(data)
    return recommendation.model_dump(mode="json", exclude_none=True)


def recommendation_json_schema() -> str:
    """프롬프트와 런타임 검증이 같은 추천 스키마를 바라보게 한다."""

    return json.dumps(
        _RECOMMENDATION_ADAPTER.json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
