import shutil
from pathlib import Path
from typing import Any, Dict

import sqlalchemy as sa
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import BadRequestError
from app.models.candidate_profile import CandidateProfile
from app.models.candidate_profile import (
    WorkExperience,
    Education,
    CandidateSkill,
    Certificate,
)
from app.models.user import User
from app.models.vacancy import Vacancy
from app.services.resumes.resume_parser import parse_resume
from app.services.resumes.resume_recommendations import analyze_resume_improvements
from app.services.resumes.resume_structurer import build_profile_from_resume_text
from app.services.candidate.resume_parser_service import ResumeParserService

ALLOWED_RESUME_EXTENSIONS = [".docx", ".pdf"]


async def _get_candidate_profile(
        session: AsyncSession,
        user: User,
) -> CandidateProfile | None:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    return result.scalar_one_or_none()


def _calculate_profile_completion(profile: CandidateProfile | None) -> float:
    """
    Очень простой расчёт заполненности профиля по ключевым полям.
    """
    if profile is None:
        return 0.0

    fields = [
        profile.phone,
        profile.city,
        profile.desired_position,
        profile.desired_salary,
        profile.about_me,
    ]
    total = len(fields)
    filled = sum(1 for f in fields if f not in (None, "", []))

    # опыт, образование, навыки, портфолио как отдельные «слоты»
    extra_slots = 4
    total += extra_slots
    if profile.experiences:
        filled += 1
    if profile.educations:
        filled += 1
    if profile.skills:
        filled += 1
    if profile.portfolio_items:
        filled += 1

    return round((filled / total) * 100.0, 1) if total > 0 else 0.0


async def get_resume_summary_for_candidate(
        session: AsyncSession,
        candidate: User,
) -> Dict[str, Any]:
    # базовая инфа по резюме/профилю
    has_resume = candidate.resume_text is not None
    resume_text_length = len(candidate.resume_text or "")

    profile = await _get_candidate_profile(session=session, user=candidate)
    profile_completion = _calculate_profile_completion(profile)

    # считаем рекомендации только если есть резюме и есть вакансии
    recommendations: Dict[str, Any] | None = None
    if candidate.resume_text:
        v_result = await session.execute(
            select(Vacancy).where(Vacancy.is_active.is_(True))
        )
        vacancies = v_result.scalars().all()

        if vacancies:
            all_vacancy_skills = [v.required_skills for v in vacancies]
            recommendations = analyze_resume_improvements(
                resume_text=candidate.resume_text,
                all_vacancy_skills=all_vacancy_skills,
            )

    return {
        "has_resume": has_resume,
        "resume_path": candidate.resume_path,
        "resume_text_length": resume_text_length,
        "profile_completion_percent": profile_completion,
        "recommendations": recommendations,
    }


async def handle_resume_upload(
    session: AsyncSession,
    user: User,
    file: UploadFile,
) -> Dict[str, Any]:
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_RESUME_EXTENSIONS:
        raise BadRequestError(
            message="Invalid resume file format",
            code="INVALID_RESUME_FORMAT",
            details={
                "allowed_extensions": ALLOWED_RESUME_EXTENSIONS,
                "got_extension": file_ext,
            },
        )

    upload_dir = Path(settings.UPLOAD_DIR) / "resumes"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"user_{user.id}_{file.filename}".replace(" ", "_")
    file_path = upload_dir / safe_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1) Парсим резюме в текст
    resume_text = parse_resume(str(file_path))

    # 2) Обновляем пользователя
    user.resume_path = str(file_path)
    user.resume_text = resume_text

    # 3) Создаём профиль если нет
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    relative_path = str(Path("resumes") / safe_name)
    profile.resume_file_path = relative_path

    # 4) LLM-парсинг — заполняет профиль сам
    parser_service = ResumeParserService(session)
    await parser_service.parse_and_save(
        user_id=user.id,
        resume_text=resume_text,
        resume_path=relative_path,
    )

    # 5) Единый коммит
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return {
        "file_path": relative_path,
        "extracted_text_length": len(resume_text),
    }
