from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_candidate
from app.models import Application
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.schemas.notification import NotificationRead
from app.schemas.resume_recommendation import ResumeRecommendationsRead
from app.schemas.vacancy import VacancyRead, VacancyWithMatchScore
from app.services.candidate.applications import (
    create_application_for_candidate,
    get_open_vacancies,
    get_recommended_vacancies_for_candidate,
    get_vacancy_for_candidate,
)
from app.services.resumes.resume_recommendations import get_resume_recommendations_for_candidate
from app.services.candidate.resume_center import handle_resume_upload
from app.services.notifications.notifications import (
    get_notifications_for_user,
    mark_notification_as_read_for_user,
)

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    result = await handle_resume_upload(
        session=session,
        user=current_user,
        file=file,
    )
    return {
        "message": "Resume uploaded successfully",
        **result,
    }


@router.post("/applications", response_model=ApplicationRead, status_code=201)
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_application_for_candidate(
        session=session,
        current_user=current_user,
        application_data=application_data,
    )


@router.get("/applications", response_model=List[ApplicationRead])
async def get_my_applications(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await session.scalars(
        select(Application).where(Application.candidate_id == current_user.id)
    )


@router.get("/notifications", response_model=List[NotificationRead])
async def get_notifications(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_notifications_for_user(
        session=session,
        user=current_user,
    )


@router.patch("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await mark_notification_as_read_for_user(
        session=session,
        user=current_user,
        notification_id=notification_id,
    )


@router.get("/vacancies", response_model=List[VacancyRead])
async def get_open_vacancies_endpoint(
    session: AsyncSession = Depends(get_async_session),
):
    return await get_open_vacancies(session=session)


@router.get("/vacancies/recommended", response_model=List[VacancyWithMatchScore])
async def get_recommended_vacancies(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
    min_score: float = Query(
        0.0,
        ge=0.0,
        le=100.0,
        description="Минимальный процент совпадения (0-100)",
    ),
):
    return await get_recommended_vacancies_for_candidate(
        session=session,
        current_user=current_user,
        min_score=min_score,
    )


@router.get("/resume/recommendations", response_model=ResumeRecommendationsRead)
async def get_resume_recommendations(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_resume_recommendations_for_candidate(
        session=session,
        current_user=current_user,
    )


@router.get("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def get_open_vacancy(
    vacancy_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_vacancy_for_candidate(
        session=session,
        candidate=current_user,
        vacancy_id=vacancy_id,
    )
