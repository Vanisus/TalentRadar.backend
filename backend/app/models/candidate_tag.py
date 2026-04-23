# app/models/candidate_tag.py
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class CandidateTag(Base):
    __tablename__ = "candidate_tags"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(ForeignKey("users.id"), nullable=False)
    hr_id = Column(ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
