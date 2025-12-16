from typing import Optional
import re

from fastapi_users import schemas
from pydantic import Field, model_validator, field_validator

from app.models.user import UserRole


class UserRead(schemas.BaseUser[int]):
    role: UserRole
    is_blocked: bool
    full_name: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    role: UserRole = Field(default=UserRole.CANDIDATE)
    full_name: Optional[str] = Field(
        None,
        description="ФИО в формате: Фамилия Имя Отчество (только русские буквы)"
    )
    password_confirm: str = Field(..., min_length=1, description="Подтверждение пароля")

    @field_validator('full_name')
    @classmethod
    def validate_full_name_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # Проверка на кириллические буквы и пробелы
        cyrillic_pattern = re.compile(r'^[А-ЯЁа-яё\s]+$')
        if not cyrillic_pattern.match(v):
            raise ValueError('ФИО должно содержать только русские буквы')
        
        # Разбиваем на слова по пробелам
        parts = v.strip().split()
        
        # Проверяем, что ровно 3 слова
        if len(parts) != 3:
            raise ValueError('ФИО должно быть в формате: Фамилия Имя Отчество')
        
        # Проверяем, что каждое слово начинается с заглавной буквы
        for part in parts:
            if not part[0].isupper():
                raise ValueError('Каждое слово в ФИО должно начинаться с заглавной буквы')
        
        return v

    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Пароли не совпадают')
        return self


class UserUpdate(schemas.BaseUserUpdate):
    role: UserRole | None = None
    full_name: Optional[str] = Field(
        None,
        description="ФИО в формате: Фамилия Имя Отчество (только русские буквы)"
    )

    @field_validator('full_name')
    @classmethod
    def validate_full_name_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # Проверка на кириллические буквы и пробелы
        cyrillic_pattern = re.compile(r'^[А-ЯЁа-яё\s]+$')
        if not cyrillic_pattern.match(v):
            raise ValueError('ФИО должно содержать только русские буквы')
        
        # Разбиваем на слова по пробелам
        parts = v.strip().split()
        
        # Проверяем, что ровно 3 слова
        if len(parts) != 3:
            raise ValueError('ФИО должно быть в формате: Фамилия Имя Отчество')
        
        # Проверяем, что каждое слово начинается с заглавной буквы
        for part in parts:
            if not part[0].isupper():
                raise ValueError('Каждое слово в ФИО должно начинаться с заглавной буквы')
        
        return v
