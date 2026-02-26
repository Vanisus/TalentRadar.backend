# app/models/saved_search.py
class SavedCandidateSearch(Base):
    __tablename__ = "saved_candidate_searches"

    id = Column(Integer, primary_key=True)
    hr_id = Column(ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    params = Column(JSON, nullable=False)  # skills, has_resume, is_active, ...
    created_at = Column(DateTime, default=datetime.utcnow)
