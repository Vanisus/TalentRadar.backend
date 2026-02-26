import shutil
from pathlib import Path
from typing import Any, Dict

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import BadRequestError
from app.models.candidate_profile import (
    CandidateProfile,
    WorkExperience,
    Education,
    CandidateSkill,
    Certificate,
)
from app.models.user import User
from app.services.resumes.resume_parser import parse_resume
from app.services.resumes.resume_structurer import build_profile_from_resume_text


ALLOWED_RESUME_EXTENSIONS = [".docx", ".pdf"]


async def handle_resume_upload(
    session: AsyncSession,
    user: User,
    file,
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

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"user_{user.id}_{file.filename}"

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Парсим резюме в текст
    resume_text = parse_resume(str(file_path))

    # Обновляем пользователя
    user.resume_path = str(file_path)
    user.resume_text = resume_text
    await session.commit()

    # Структурируем в профиль
    structured = build_profile_from_resume_text(resume_text)

    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    # Обновляем базовые поля профиля
    for field, value in structured["profile"].items():
        setattr(profile, field, value)

    # Чистим старые записи
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

    # Создаём новые сущности
    for exp in structured["experiences"]:
        session.add(WorkExperience(profile_id=profile.id, **exp))

    for edu in structured["educations"]:
        session.add(Education(profile_id=profile.id, **edu))

    for sk in structured["skills"]:
        session.add(CandidateSkill(profile_id=profile.id, **sk))

    for cert in structured["certificates"]:
        session.add(Certificate(profile_id=profile.id, **cert))

    await session.commit()

    return {
        "file_path": str(file_path),
        "extracted_text_length": len(resume_text),
    }
