from typing import List
from pydantic import BaseModel, Field


class ResumeRecommendationsRead(BaseModel):
    recommendations: List[str] = Field(
        ...,
        description="Список рекомендаций по улучшению резюме",
    )
