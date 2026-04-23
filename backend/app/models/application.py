from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Enum as SQLEnum, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApplicationStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_applications_pipeline_stage", "pipeline_stage"),
        Index("ix_applications_rating", "rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Связи
    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id"), nullable=False)
    candidate_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Статус и соответствие
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus),
        default=ApplicationStatus.NEW,
        nullable=False
    )
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Этап воронки (например: new, screening, interview, offer, rejected)
    pipeline_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    match_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="applications")
