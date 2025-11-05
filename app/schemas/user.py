from fastapi_users import schemas
from pydantic import Field

from app.models.user import UserRole


class UserRead(schemas.BaseUser[int]):
    role: UserRole
    is_blocked: bool


class UserCreate(schemas.BaseUserCreate):
    role: UserRole = Field(default=UserRole.CANDIDATE)


class UserUpdate(schemas.BaseUserUpdate):
    role: UserRole | None = None
