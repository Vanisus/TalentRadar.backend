from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CandidateNote(Base):
    __tablename__ = "candidate_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    hr_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Краткий заголовок или тег заметки (опционально)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Основной текст заметки
    body: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Связи на User (кандидат и HR)
    candidate = relationship(
        "User",
        foreign_keys=[candidate_id],
        lazy="joined",
    )
    hr = relationship(
        "User",
        foreign_keys=[hr_id],
        lazy="joined",
    )
    @hybrid_property
    def author_name(self) -> str | None:
        return self.hr.full_name if self.hr else None
