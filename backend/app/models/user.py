from datetime import datetime, timezone
from enum import Enum
from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from typing import TYPE_CHECKING
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from app.models.candidate_profile import CandidateProfile


class UserRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    CANDIDATE = "candidate"


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Дополнительные поля
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.CANDIDATE,
        nullable=False
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Для кандидатов
    resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    parsed_resumes = relationship("ParsedResume", back_populates="user", cascade="all, delete-orphan")
    # Новый one-to-one профиль кандидата
    profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        uselist=False,
        back_populates="user",
    )
