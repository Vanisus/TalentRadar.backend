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
    """
    Сохранить файл резюме, распарсить текст, обновить User и структурированный профиль.
    Возвращает короткую сводку для ответа API.
    """
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

    # 2) Обновляем пользователя (если нужно хранить текст и путь в User)
    user.resume_path = str(file_path)
    user.resume_text = resume_text

    # 3) Структурируем профиль
    structured = build_profile_from_resume_text(resume_text)

    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    # 3.1) Сохраняем путь к файлу резюме в профиле
    # относительный путь от UPLOAD_DIR: 'resumes/user_1_cv.pdf'
    relative_path = str(Path("resumes") / safe_name)
    profile.resume_file_path = relative_path

    # 3.2) Обновляем базовые поля профиля из structured["profile"]
    for field, value in structured["profile"].items():
        setattr(profile, field, value)

    # 3.3) Чистим старые записи
    await session.execute(
        sa.delete(WorkExperience).where(WorkExperience.profile_id == profile.id)
    )
    await session.execute(
        sa.delete(Education).where(Education.profile_id == profile.id)
    )
    await session.execute(
        sa.delete(CandidateSkill).where(CandidateSkill.profile_id == profile.id)
    )
    await session.execute(
        sa.delete(Certificate).where(Certificate.profile_id == profile.id)
    )

    # 3.4) Создаём новые сущности
    for exp in structured["experiences"]:
        session.add(WorkExperience(profile_id=profile.id, **exp))

    for edu in structured["educations"]:
        session.add(Education(profile_id=profile.id, **edu))

    for sk in structured["skills"]:
        session.add(CandidateSkill(profile_id=profile.id, **sk))

    for cert in structured["certificates"]:
        session.add(Certificate(profile_id=profile.id, **cert))

    # 4) Один общий коммит
    await session.commit()

    return {
        "file_path": relative_path,
        "extracted_text_length": len(resume_text),
    }
