from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session, async_session_maker
from app.dependencies import get_current_candidate
from app.models import Application
from app.models.parsed_resume import ParsedResume
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.schemas.notification import NotificationRead
from app.schemas.parsed_resume import ParsedResumeRead
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

from app.services.llm.application_analysis import _build_vacancy_text

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


@router.get("/resume/parsed", response_model=ParsedResumeRead)
async def get_parsed_resume(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает последний результат LLM-парсинга резюме текущего кандидата.
    parse_status: 'pending' | 'success' | 'failed'
    """
    result = await session.execute(
        select(ParsedResume)
        .where(ParsedResume.user_id == current_user.id)
        .order_by(ParsedResume.created_at.desc())
        .limit(1)
    )
    parsed = result.scalar_one_or_none()
    if parsed is None:
        raise HTTPException(status_code=404, detail="No parsed resume found. Upload a resume first.")
    return parsed


@router.post("/applications", response_model=ApplicationRead, status_code=201)
async def create_application(
    application_data: ApplicationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    application = await create_application_for_candidate(
        session=session,
        current_user=current_user,
        application_data=application_data,
    )

    # Загружаем вакансию для передачи в фон
    from sqlalchemy import select
    from app.models.vacancy import Vacancy
    result = await session.execute(select(Vacancy).where(Vacancy.id == application_data.vacancy_id))
    vacancy = result.scalar_one()

    background_tasks.add_task(
        run_llm_match_score,
        application_id=application.id,
        vacancy_id=vacancy.id,
        hr_id=vacancy.hr_id,
        vacancy_title=vacancy.title,
        vacancy_text=_build_vacancy_text(vacancy),
        resume_text=current_user.resume_text,
        candidate_id=current_user.id,
        candidate_name=current_user.full_name or current_user.email,
        session_factory=async_session_maker,
    )

    return application


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
    session: AsyncSession = Depends(get_async_session),
    current_candidate: User = Depends(get_current_candidate),
):
    return await get_vacancy_for_candidate(
        session=session,
        vacancy_id=vacancy_id,
    )
