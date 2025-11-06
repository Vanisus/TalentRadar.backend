from typing import Optional

from fastapi_users import schemas
from pydantic import Field

from app.models.user import UserRole


class UserRead(schemas.BaseUser[int]):
    role: UserRole
    is_blocked: bool
    full_name: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    role: UserRole = Field(default=UserRole.CANDIDATE)
    full_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    role: UserRole | None = None
    full_name: Optional[str] = None
