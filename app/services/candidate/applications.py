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
from app.services.resumes.resume_recommendations import analyze_resume_improvements


async def create_application_for_candidate(
    session: AsyncSession,
    current_user: User,
    application_data: ApplicationCreate,
) -> Application:
    # Вакансия
    result = await session.execute(
        select(Vacancy).where(Vacancy.id == application_data.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()

    if not vacancy:
        raise NotFoundError(
            message="Vacancy not found",
            code="VACANCY_NOT_FOUND",
            details={"vacancy_id": application_data.vacancy_id},
        )

    if not vacancy.is_active:
        raise ValidationError(
            message="Vacancy is not active",
            code="VACANCY_INACTIVE",
            details={"vacancy_id": vacancy.id},
        )

    # Дубликат
    result = await session.execute(
        select(Application).where(
            Application.vacancy_id == application_data.vacancy_id,
            Application.candidate_id == current_user.id,
        )
    )
    existing_application = result.scalar_one_or_none()
    if existing_application:
        raise ConflictError(
            message="You have already applied to this vacancy",
            code="APPLICATION_ALREADY_EXISTS",
            details={
                "vacancy_id": application_data.vacancy_id,
                "candidate_id": current_user.id,
            },
        )

    # Резюме обязательно
    if not current_user.resume_text:
        raise ValidationError(
            message="Please upload your resume first",
            code="RESUME_REQUIRED",
            details={"candidate_id": current_user.id},
        )

    # match_score
    match_score = calculate_match_score(
        resume_text=current_user.resume_text,
        required_skills=vacancy.required_skills,
    )

    # Заявка
    application = Application(
        vacancy_id=application_data.vacancy_id,
        candidate_id=current_user.id,
        match_score=match_score,
    )
    session.add(application)

    # Уведомление кандидату
    if match_score >= 70:
        message = f"Отлично! Вы подходите на вакансию '{vacancy.title}' на {match_score:.0f}%"
    elif match_score >= 50:
        message = f"Вы подходите на вакансию '{vacancy.title}' на {match_score:.0f}%"
    else:
        message = (
            f"К сожалению, ваш профиль соответствует вакансии '{vacancy.title}' "
            f"только на {match_score:.0f}%"
        )

    session.add(
        Notification(
            user_id=current_user.id,
            message=message,
        )
    )

    # Уведомление HR
    if match_score >= 50:
        candidate_name = current_user.full_name or current_user.email
        hr_message = (
            f"На вакансию '{vacancy.title}' откликнулся подходящий кандидат: "
            f"{candidate_name}. Совпадение: {match_score:.0f}%"
        )
        session.add(
            Notification(
                user_id=vacancy.hr_id,
                message=hr_message,
            )
        )

    await session.commit()
    await session.refresh(application)
    return application


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

    vacancies = await get_open_vacancies(session=session)

    recommended: List[VacancyWithMatchScore] = []
    for vacancy in vacancies:
        match_score = calculate_match_score(
            resume_text=current_user.resume_text,
            required_skills=vacancy.required_skills,
        )
        if match_score < min_score:
            continue

        recommended.append(
            VacancyWithMatchScore(
                id=vacancy.id,
                title=vacancy.title,
                description=vacancy.description,
                required_skills=vacancy.required_skills,
                hr_id=vacancy.hr_id,
                is_active=vacancy.is_active,
                created_at=vacancy.created_at,
                updated_at=vacancy.updated_at,
                match_score=match_score,
            )
        )

    recommended.sort(key=lambda x: x.match_score, reverse=True)
    return recommended


async def get_resume_recommendations_for_candidate(
    session: AsyncSession,
    current_user: User,
) -> ResumeRecommendationsRead:
    if not current_user.resume_text:
        raise ValidationError(
            message="Please upload your resume first to get recommendations",
            code="RESUME_REQUIRED",
            details={"candidate_id": current_user.id},
        )

    vacancies = await get_open_vacancies(session=session)
    if not vacancies:
        raise NotFoundError(
            message="No active vacancies found for analysis",
            code="NO_ACTIVE_VACANCIES",
        )

    all_vacancy_skills = [v.required_skills for v in vacancies]

    return analyze_resume_improvements(
        resume_text=current_user.resume_text,
        all_vacancy_skills=all_vacancy_skills,
    )


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
