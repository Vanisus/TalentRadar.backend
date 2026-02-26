from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_candidate
from app.models.application import Application
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.schemas.notification import NotificationRead
from app.schemas.resume_recommendation import ResumeRecommendation
from app.schemas.vacancy import VacancyRead, VacancyWithMatchScore
from app.services.applications import (
    create_application_for_candidate,
    get_open_vacancies,
    get_recommended_vacancies_for_candidate,
    get_resume_recommendations_for_candidate,
    VacancyNotFoundError,
    VacancyInactiveError,
    DuplicateApplicationError,
    ResumeRequiredError,
)
from app.services.candidates import handle_resume_upload, ResumeFormatError
from app.services.notifications import (
    get_notifications_for_user,
    mark_notification_as_read_for_user,
)

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("/resume", status_code=status.HTTP_200_OK)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """Загрузка резюме (docx или pdf) + авто-заполнение профиля кандидата."""
    try:
        result = await handle_resume_upload(
            session=session,
            user=current_user,
            file=file,
        )
    except ResumeFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "message": "Resume uploaded successfully",
        **result,
    }


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """Подача заявки на вакансию"""
    try:
        application = await create_application_for_candidate(
            session=session,
            current_user=current_user,
            application_data=application_data,
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )
    except VacancyInactiveError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vacancy is not active",
        )
    except DuplicateApplicationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this vacancy",
        )
    except ResumeRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first",
        )

    return application


@router.get("/applications", response_model=list[ApplicationRead])
async def get_my_applications(
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все свои заявки со статусами"""
    result = await session.execute(
        select(Application).where(Application.candidate_id == current_user.id)
    )
    applications = result.scalars().all()
    return applications


@router.get("/notifications", response_model=list[NotificationRead])
async def get_notifications(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить все уведомления"""
    notifications = await get_notifications_for_user(
        session=session,
        user=current_user,
    )
    return notifications


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """Отметить уведомление как прочитанное"""
    try:
        await mark_notification_as_read_for_user(
            session=session,
            user=current_user,
            notification_id=notification_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )



@router.get("/vacancies", response_model=list[VacancyRead])
async def get_open_vacancies_endpoint(
    session: AsyncSession = Depends(get_async_session),
):
    """Получить все открытые вакансии (is_active=True)"""
    vacancies = await get_open_vacancies(session=session)
    return vacancies


@router.get("/vacancies/recommended", response_model=list[VacancyWithMatchScore])
async def get_recommended_vacancies(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Минимальный процент совпадения (0-100)"),
):
    """Получить рекомендованные вакансии на основе ключевых слов из резюме"""
    try:
        vacancies = await get_recommended_vacancies_for_candidate(
            session=session,
            current_user=current_user,
            min_score=min_score,
        )
    except ResumeRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first to get recommendations",
        )

    return vacancies



@router.get("/resume/recommendations", response_model=ResumeRecommendation)
async def get_resume_recommendations(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить рекомендации по улучшению резюме на основе анализа популярных навыков в вакансиях"""
    try:
        recommendations_data = await get_resume_recommendations_for_candidate(
            session=session,
            current_user=current_user,
        )
    except ResumeRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first to get recommendations",
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active vacancies found for analysis",
        )

    return recommendations_data


@router.get("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def get_open_vacancy(
        vacancy_id: int,
        session: AsyncSession = Depends(get_async_session),
):
    """Получить одну открытую вакансию по id (для кандидата)"""
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.is_active == True
        )
    )
    vacancy = result.scalar_one_or_none()

    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )

    return vacancy
