import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.models.application import Application
from app.models.notification import Notification
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.application import ApplicationCreate
from app.schemas.resume_recommendation import ResumeRecommendationsRead
from app.schemas.vacancy import VacancyWithMatchScore
from app.services.analytics.match_score import calculate_match_score
from app.services.llm.client import call_llm_service
from app.services.llm.application_analysis import _build_vacancy_text
from app.services.resumes.resume_recommendations import analyze_resume_improvements

logger = logging.getLogger(__name__)


async def create_application_for_candidate(
    session: AsyncSession,
    current_user: User,
    application_data: ApplicationCreate,
) -> Application:
    result = await session.execute(
        select(Vacancy).where(Vacancy.id == application_data.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()
    if not vacancy:
        raise NotFoundError("Vacancy not found", "VACANCY_NOT_FOUND", {"vacancy_id": application_data.vacancy_id})
    if not vacancy.is_active:
        raise ValidationError("Vacancy is not active", "VACANCY_INACTIVE", {"vacancy_id": vacancy.id})

    result = await session.execute(
        select(Application).where(
            Application.vacancy_id == application_data.vacancy_id,
            Application.candidate_id == current_user.id,
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError(
            "You have already applied to this vacancy",
            "APPLICATION_ALREADY_EXISTS",
            {"vacancy_id": application_data.vacancy_id, "candidate_id": current_user.id},
        )

    if not current_user.resume_text:
        raise ValidationError("Please upload your resume first", "RESUME_REQUIRED", {"candidate_id": current_user.id})

    application = Application(
        vacancy_id=application_data.vacancy_id,
        candidate_id=current_user.id,
        match_score=0.0,
        match_summary=None,
    )
    session.add(application)

    # Простое подтверждение отклика — без match_score, он кандидату не нужен
    session.add(Notification(
        user_id=current_user.id,
        message=f"Вы успешно откликнулись на вакансию «{vacancy.title}».",
    ))

    await session.commit()
    await session.refresh(application)
    return application


async def run_llm_match_score(
    application_id: int,
    vacancy_id: int,
    hr_id: int,
    vacancy_title: str,
    vacancy_text: str,
    resume_text: str,
    candidate_id: int,
    candidate_name: str,
    session_factory,
) -> None:
    """
    Background task: calls LLM, updates match_score + match_summary.
    Notifies HR only — candidate sees match_score before applying, not after.
    """
    async with session_factory() as session:
        try:
            llm_response = await call_llm_service(
                vacancy_text=vacancy_text,
                resume_text=resume_text,
            )
            raw_score = llm_response.get("score")
            match_score = round(float(raw_score) * 100, 2) if raw_score is not None else 0.0
            match_summary = llm_response.get("raw_output")
        except Exception as e:
            logger.warning(f"[LLM background] match_score failed for application {application_id}: {e}")
            return

        result = await session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            return

        application.match_score = match_score
        application.match_summary = match_summary

        # Уведомляем только HR — кандидату match_score показывался до отклика, после он не нужен
        if match_score >= 50:
            session.add(Notification(
                user_id=hr_id,
                message=(
                    f"На вакансию «{vacancy_title}» откликнулся подходящий кандидат: "
                    f"{candidate_name}. Совпадение: {match_score:.0f}%"
                ),
            ))

        await session.commit()
        logger.info(f"[LLM background] application {application_id} scored: {match_score}")


async def get_candidate_applications(
    session: AsyncSession,
    current_user: User,
) -> List[Application]:
    result = await session.execute(
        select(Application).where(Application.candidate_id == current_user.id)
    )
    return list(result.scalars().all())


async def get_open_vacancies(session: AsyncSession) -> List[Vacancy]:
    result = await session.execute(
        select(Vacancy).where(Vacancy.is_active == True)
    )
    return list(result.scalars().all())


async def get_vacancies_with_match_score(
    session: AsyncSession,
    current_user: User,
) -> List[VacancyWithMatchScore]:
    """
    Список всех активных вакансий с быстрым match_score (calculate_match_score, без LLM).
    match_score показывается кандидату только ДО отклика (и только если >= 50%).
    """
    vacancies = await get_open_vacancies(session=session)
    result = []
    for vacancy in vacancies:
        score = 0.0
        if current_user.resume_text:
            score = calculate_match_score(
                resume_text=current_user.resume_text,
                required_skills=vacancy.required_skills,
            )
        result.append(
            VacancyWithMatchScore(
                id=vacancy.id,
                title=vacancy.title,
                description=vacancy.description,
                required_skills=vacancy.required_skills,
                hr_id=vacancy.hr_id,
                is_active=vacancy.is_active,
                created_at=vacancy.created_at,
                updated_at=vacancy.updated_at,
                match_score=score,
            )
        )
    result.sort(key=lambda x: x.match_score, reverse=True)
    return result


async def get_recommended_vacancies_for_candidate(
    session: AsyncSession,
    current_user: User,
    min_score: float,
) -> List[VacancyWithMatchScore]:
    if not current_user.resume_text:
        raise ValidationError(
            message="Please upload your resume first to get recommendations",
            code="RESUME_REQUIRED",
            details={"candidate_id": current_user.id},
        )
    all_vacancies = await get_vacancies_with_match_score(session=session, current_user=current_user)
    return [v for v in all_vacancies if v.match_score >= min_score]


async def get_vacancy_for_candidate(
    session: AsyncSession,
    vacancy_id: int,
) -> Vacancy:
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.is_active.is_(True),
        )
    )
    vacancy = result.scalar_one_or_none()
    if vacancy is None:
        raise NotFoundError(
            message="Vacancy not found",
            code="VACANCY_NOT_FOUND",
            details={"vacancy_id": vacancy_id},
        )
    return vacancy
