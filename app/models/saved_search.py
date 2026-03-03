# app/models/saved_search.py

from sqlalchemy import Column, Integer, ForeignKey, String, JSON, DateTime, func

from app.database import Base


class SavedCandidateSearch(Base):
    __tablename__ = "saved_candidate_searches"

    id = Column(Integer, primary_key=True)
    hr_id = Column(ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    params = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
