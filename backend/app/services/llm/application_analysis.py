# app/services/llm/application_analysis.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ForbiddenError
from app.models.application import Application
from app.models.user import User
from app.models.candidate_profile import CandidateProfile
from app.services.llm.client import call_llm_service


async def analyze_application_with_llm(
    session: AsyncSession,
    hr: User,
    application_id: int,
):
    result = await session.execute(
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.vacancy))
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise NotFoundError("Application not found", "APP_NOT_FOUND", {"application_id": application_id})

    vacancy = application.vacancy

    if vacancy.hr_id != hr.id:
        raise ForbiddenError("Access denied", "FORBIDDEN", {"application_id": application_id})

    # Грузим кандидата с профилем и всеми вложенными связями за один запрос
    cand_result = await session.execute(
        select(User)
        .where(User.id == application.candidate_id)
        .options(
            selectinload(User.profile).options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.experiences),
                selectinload(CandidateProfile.educations),
            )
        )
    )
    candidate = cand_result.scalar_one_or_none()
    if candidate is None:
        raise NotFoundError("Candidate not found", "CANDIDATE_NOT_FOUND", {"candidate_id": application.candidate_id})

    vacancy_text = _build_vacancy_text(vacancy)
    resume_text = _build_resume_text(candidate)

    llm_response = await call_llm_service(vacancy_text, resume_text)
    raw_output = llm_response["raw_output"]
    score = llm_response.get("score")

    application.match_summary = raw_output
    if score is not None:
        application.match_score = round(float(score) * 100, 2)

    await session.commit()
    await session.refresh(application)

    return {
        "application_id": application.id,
        "match_score": application.match_score,
        "llm_summary": application.match_summary,
    }


def _build_vacancy_text(vacancy) -> str:
    parts = [
        f"Название: {vacancy.title}",
        f"Описание: {vacancy.description or ''}",
        f"Требуемые навыки: {', '.join(vacancy.required_skills or [])}",
    ]
    return "\n".join(parts)


def _build_resume_text(candidate: User) -> str:
    chunks = []
    if candidate.full_name:
        chunks.append(f"ФИО: {candidate.full_name}")
    if candidate.resume_text:
        chunks.append(f"Текст резюме (raw):\n{candidate.resume_text}")

    profile = candidate.profile
    if profile:
        if profile.desired_position:
            chunks.append(f"Желаемая должность: {profile.desired_position}")
        if profile.city:
            chunks.append(f"Город: {profile.city}")
        if profile.skills:
            skills = [s.name for s in profile.skills]
            chunks.append(f"Навыки профиля: {', '.join(skills)}")

        if profile.experiences:
            lines = []
            for e in profile.experiences:
                lines.append(
                    f"- {e.position} в {e.company} ({e.start_date} — "
                    f"{'\u043d.в.' if e.is_current else e.end_date}): {e.description or ''}"
                )
            chunks.append("Опыт работы:\n" + "\n".join(lines))

        if profile.educations:
            lines = []
            for ed in profile.educations:
                lines.append(
                    f"- {ed.institution}, {ed.degree or ''} ({ed.start_year}\u2013{ed.end_year})"
                )
            chunks.append("Образование:\n" + "\n".join(lines))

    return "\n\n".join(chunks)
