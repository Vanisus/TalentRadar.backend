from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.candidate_profile import (
    WorkExperienceRead,
    EducationRead,
    CandidateSkillRead,
    CertificateRead,
    PortfolioItemRead,
)


class HRCandidateShort(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    city: Optional[str] = None
    desired_position: Optional[str] = None
    desired_salary: Optional[int] = None
    has_portfolio: bool
    total_experience_years: float

    class Config:
        from_attributes = True


class HRCandidateProfile(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    telegram: Optional[str] = None

    city: Optional[str] = None
    desired_position: Optional[str] = None
    desired_salary: Optional[int] = None

    about_me: Optional[str] = None
    birth_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    experiences: List[WorkExperienceRead] = []
    educations: List[EducationRead] = []
    skills: List[CandidateSkillRead] = []
    certificates: List[CertificateRead] = []
    portfolio_items: List[PortfolioItemRead] = []

    class Config:
        from_attributes = True
