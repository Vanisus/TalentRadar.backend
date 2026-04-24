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

    # Создаём отклик мгновенно — LLM посчитает в фоне
    application = Application(
        vacancy_id=application_data.vacancy_id,
        candidate_id=current_user.id,
        match_score=0.0,
        match_summary=None,
    )
    session.add(application)

    # Уведомление кандидату — сразу, без скора
    session.add(Notification(
        user_id=current_user.id,
        message=f"Вы успешно откликнулись на вакансию «{vacancy.title}». Анализ соответствия выполняется...",
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
    """Фоновая задача: вызывает LLM и обновляет match_score + match_summary."""
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

        # Уведомление кандидату с реальным результатом
        if match_score >= 70:
            candidate_msg = f"Анализ завершён: вы подходите на вакансию «{vacancy_title}» на {match_score:.0f}%"
        elif match_score >= 50:
            candidate_msg = f"Анализ завершён: вы подходите на вакансию «{vacancy_title}» на {match_score:.0f}%"
        else:
            candidate_msg = f"Анализ завершён: ваш профиль соответствует вакансии «{vacancy_title}» на {match_score:.0f}%"

        session.add(Notification(user_id=candidate_id, message=candidate_msg))

        # Уведомление HR если кандидат подходит
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
