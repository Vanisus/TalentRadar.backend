# app/schemas/parsed_resume.py
from pydantic import BaseModel, Field
from typing import Optional

class ResumeContactSchema(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None

class ResumeLanguageSchema(BaseModel):
    name: str
    level: Optional[str] = None

class ResumeExperienceSchema(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    duration_months: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    technologies: list[str] = []
    achievements: list[str] = []

class ResumeEducationSchema(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class ResumeCertificateSchema(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None

class ResumeProjectSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: list[str] = []
    url: Optional[str] = None

class ResumeRawSectionsSchema(BaseModel):
    about: Optional[str] = None
    skills_block: Optional[str] = None
    experience_block: Optional[str] = None
    education_block: Optional[str] = None

class ParsedResumePayload(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    contacts: ResumeContactSchema = Field(default_factory=ResumeContactSchema)
    summary: Optional[str] = None
    desired_position: Optional[str] = None
    employment_type: Optional[str] = None
    work_format: Optional[str] = None
    total_experience_months: Optional[int] = None
    skills_hard: list[str] = []
    skills_soft: list[str] = []
    languages: list[ResumeLanguageSchema] = []
    work_experience: list[ResumeExperienceSchema] = []
    education: list[ResumeEducationSchema] = []
    certificates: list[ResumeCertificateSchema] = []
    projects: list[ResumeProjectSchema] = []
    portfolio_links: list[str] = []
    raw_sections: ResumeRawSectionsSchema = Field(default_factory=ResumeRawSectionsSchema)