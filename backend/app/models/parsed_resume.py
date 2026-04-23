# app/models/parsed_resume.py
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    source_resume_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    parse_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)

    parsed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    normalized_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="parsed_resumes")