# app/models/application_event.py
from datetime import UTC, datetime

from sqlalchemy import Column, Integer, ForeignKey, String, JSON, DateTime

from app.database import Base


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id = Column(Integer, primary_key=True)
    application_id = Column(ForeignKey("applications.id"), nullable=False)
    type = Column(String, nullable=False)  # CREATED, STATUS_CHANGED, HR_VIEWED, NOTE_ADDED
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
