from typing import Literal

from pydantic import BaseModel, Field


FitnessLevel = Literal["초보", "중급", "고급"]
MainWorkoutType = Literal["웨이트트레이닝", "러닝", "둘다"]
Persona = Literal["angel", "tiger"]


class ProfileUpdate(BaseModel):
    fitness_goals: list[str] | None = None
    fitness_level: FitnessLevel | None = None
    main_workout_type: MainWorkoutType | None = None
    weekly_frequency: int | None = Field(default=None, ge=1, le=7)
    caution_areas: list[str] | None = None
    persona: Persona | None = None
