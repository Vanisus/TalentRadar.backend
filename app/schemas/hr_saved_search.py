from typing import Any, Dict

from pydantic import BaseModel, Field


class SavedSearchCreate(BaseModel):
    name: str = Field(..., description="Название сохранённого поиска")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Параметры поиска (skills, has_resume, is_active, ...)",
    )


class SavedSearchRead(BaseModel):
    id: int
    name: str
    params: Dict[str, Any]

    class Config:
        from_attributes = True
