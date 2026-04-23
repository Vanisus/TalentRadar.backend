from typing import List
from pydantic import BaseModel, Field


class PlatformRule(BaseModel):
    title: str = Field(..., description="Заголовок правила")
    description: str = Field(..., description="Описание правила")


class PlatformRules(BaseModel):
    rules: List[PlatformRule] = Field(..., description="Список правил платформы")
    last_updated: str = Field(..., description="Дата последнего обновления правил")

