from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkExperienceBase(BaseModel):
    company: str = Field(..., max_length=200)
    position: str = Field(..., max_length=200)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False


class WorkExperienceCreate(WorkExperienceBase):
    pass


class WorkExperienceRead(WorkExperienceBase):
    id: int

    class Config:
        from_attributes = True


class EducationBase(BaseModel):
    institution: str = Field(..., max_length=300)
    degree: Optional[str] = Field(None, max_length=100)
    field_of_study: Optional[str] = Field(None, max_length=200)
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class EducationCreate(EducationBase):
    pass


class EducationRead(EducationBase):
    id: int

    class Config:
        from_attributes = True


class CandidateSkillBase(BaseModel):
    name: str = Field(..., max_length=100)
    level: Optional[str] = Field(None, max_length=50)


class CandidateSkillCreate(CandidateSkillBase):
    pass


class CandidateSkillRead(CandidateSkillBase):
    id: int

    class Config:
        from_attributes = True


class CertificateBase(BaseModel):
    title: str = Field(..., max_length=300)
    issuer: Optional[str] = Field(None, max_length=200)
    issue_date: Optional[date] = None
    file_path: Optional[str] = None


class CertificateCreate(CertificateBase):
    pass


class CertificateRead(CertificateBase):
    id: int

    class Config:
        from_attributes = True


class PortfolioItemBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None


class PortfolioItemCreate(PortfolioItemBase):
    pass


class PortfolioItemRead(PortfolioItemBase):
    id: int

    class Config:
        from_attributes = True


class CandidateProfileBase(BaseModel):
    about_me: Optional[str] = None
    desired_position: Optional[str] = Field(None, max_length=200)
    desired_salary: Optional[int] = None
    city: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None


class CandidateProfileCreate(CandidateProfileBase):
    pass


class CandidateProfileUpdate(CandidateProfileBase):
    pass


class CandidateProfileRead(CandidateProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    experiences: List[WorkExperienceRead] = []
    educations: List[EducationRead] = []
    skills: List[CandidateSkillRead] = []
    certificates: List[CertificateRead] = []
    portfolio_items: List[PortfolioItemRead] = []

    class Config:
        from_attributes = True
