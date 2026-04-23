from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VacancyTemplate(Base):
    __tablename__ = "vacancy_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    # Связь с HR-менеджером, который создал шаблон
    hr_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

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

