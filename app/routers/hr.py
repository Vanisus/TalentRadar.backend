from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.application import ApplicationStatusUpdate, ApplicationRead
from app.schemas.candidate_analysis import VacancyApplicationsAnalysis, ApplicationAnalysis, CandidateMatchAnalysis
from app.schemas.candidate_search import CandidateSearchResult
from app.schemas.notification import NotificationRead
from app.schemas.vacancy import VacancyCreate, VacancyRead, VacancyUpdate, VacancyFromTemplate
from app.schemas.vacancy_template import VacancyTemplateCreate, VacancyTemplateRead, VacancyTemplateUpdate
from app.services.candidate_analysis import analyze_candidate_match
from app.services.hr_analytics import (
    get_vacancy_analytics_data,
    VacancyNotFoundError as AnalyticsVacancyNotFoundError,
)
from app.services.hr_search import search_candidates_for_hr, VacancyNotFoundError
from app.services.hr_templates import (
    create_template_for_hr,
    get_hr_templates,
    get_hr_template,
    update_hr_template,
    delete_hr_template,
    create_vacancy_from_template_for_hr,
    TemplateNotFoundError,
)
from app.services.hr_vacancies import (
    create_vacancy_for_hr,
    get_hr_vacancies,
    get_hr_vacancy,
    update_hr_vacancy,
    delete_hr_vacancy,
    VacancyNotFoundError,
)
from app.services.notifications import (
    get_notifications_for_user,
    mark_notification_as_read_for_user,
)
from app.services.hr_applications import (
    get_vacancy_applications_for_hr,
    update_application_status_for_hr,
    VacancyNotFoundError as AppsVacancyNotFoundError,
    ApplicationNotFoundError,
    VacancyForbiddenError,
)


router = APIRouter(prefix="/hr", tags=["HR"])


# ==================== CRUD ВАКАНСИЙ ====================

@router.post("/vacancies", response_model=VacancyRead, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
        vacancy_data: VacancyCreate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    vacancy = await create_vacancy_for_hr(
        session=session,
        hr=current_user,
        data=vacancy_data.model_dump(),
    )
    return vacancy


@router.get("/vacancies", response_model=list[VacancyRead])
async def get_my_vacancies(
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    vacancies = await get_hr_vacancies(
        session=session,
        hr=current_user,
    )
    return vacancies


@router.get("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def get_vacancy(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    try:
        vacancy = await get_hr_vacancy(
            session=session,
            hr=current_user,
            vacancy_id=vacancy_id,
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )
    return vacancy


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def update_vacancy(
        vacancy_id: int,
        vacancy_data: VacancyUpdate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    try:
        vacancy = await update_hr_vacancy(
            session=session,
            hr=current_user,
            vacancy_id=vacancy_id,
            data=vacancy_data.model_dump(exclude_unset=True),
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )
    return vacancy


@router.delete("/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    try:
        await delete_hr_vacancy(
            session=session,
            hr=current_user,
            vacancy_id=vacancy_id,
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )


# ==================== ЗАЯВКИ НА ВАКАНСИЮ ====================

@router.get("/vacancies/{vacancy_id}/applications")
async def get_vacancy_applications(
    vacancy_id: int,
    min_score: float = Query(0, ge=0, le=100, description="Минимальный match_score"),
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """Получить заявки на вакансию с фильтром по match_score"""
    try:
        data = await get_vacancy_applications_for_hr(
            session=session,
            hr=current_user,
            vacancy_id=vacancy_id,
            min_score=min_score,
        )
    except AppsVacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )

    return data



# ==================== АНАЛИТИКА ====================

@router.get("/vacancies/{vacancy_id}/analytics")
async def get_vacancy_analytics(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить аналитику по вакансии"""
    try:
        data = await get_vacancy_analytics_data(
            session=session,
            hr=current_user,
            vacancy_id=vacancy_id,
        )
    except AnalyticsVacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )

    vacancy = data["vacancy"]

    return {
        "vacancy_id": vacancy.id,
        "vacancy_title": vacancy.title,
        "vacancy_created_at": vacancy.created_at,
        "is_active": vacancy.is_active,
        "statistics": {
            "total_applications": data["total_applications"],
            "average_match_score": round(data["average_match_score"], 2),
            "status_distribution": data["status_counts"],
            "time_to_first_response": data["time_to_first_response"],
        },
    }


# ==================== ШАБЛОНЫ ВАКАНСИЙ ====================

@router.post("/templates", response_model=VacancyTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
        template_data: VacancyTemplateCreate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Создание нового шаблона вакансии"""
    template = await create_template_for_hr(
        session=session,
        hr=current_user,
        data=template_data.model_dump(),
    )
    return template


@router.get("/templates", response_model=list[VacancyTemplateRead])
async def get_my_templates(
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все шаблоны текущего HR-менеджера"""
    templates = await get_hr_templates(
        session=session,
        hr=current_user,
    )
    return templates


@router.get("/templates/{template_id}", response_model=VacancyTemplateRead)
async def get_template(
        template_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить конкретный шаблон"""
    try:
        template = await get_hr_template(
            session=session,
            hr=current_user,
            template_id=template_id,
        )
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template


@router.patch("/templates/{template_id}", response_model=VacancyTemplateRead)
async def update_template(
        template_id: int,
        template_data: VacancyTemplateUpdate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Обновление шаблона вакансии"""
    try:
        template = await update_hr_template(
            session=session,
            hr=current_user,
            template_id=template_id,
            data=template_data.model_dump(exclude_unset=True),
        )
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
        template_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Удаление шаблона вакансии"""
    try:
        await delete_hr_template(
            session=session,
            hr=current_user,
            template_id=template_id,
        )
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


@router.post(
    "/templates/{template_id}/create-vacancy",
    response_model=VacancyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_vacancy_from_template(
        template_id: int,
        vacancy_data: VacancyFromTemplate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Создать вакансию из шаблона"""
    try:
        vacancy = await create_vacancy_from_template_for_hr(
            session=session,
            hr=current_user,
            template_id=template_id,
            vacancy_data=vacancy_data,
        )
    except TemplateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return vacancy


# ==================== ПОИСК КАНДИДАТОВ ====================

@router.get("/candidates/search", response_model=list[CandidateSearchResult])
async def search_candidates(
        skills: Optional[list[str]] = Query(None, description="Список навыков для поиска в резюме"),
        has_resume: Optional[bool] = Query(None, description="Только кандидаты с загруженным резюме"),
        is_active: Optional[bool] = Query(None, description="Только активные кандидаты"),
        is_blocked: Optional[bool] = Query(False, description="Только заблокированные кандидаты (по умолчанию False)"),
        vacancy_id: Optional[int] = Query(None, description="ID вакансии для расчета match_score"),
        min_match_score: Optional[float] = Query(
            None,
            ge=0.0,
            le=100.0,
            description="Минимальный match_score с указанной вакансией",
        ),
        search_text: Optional[str] = Query(None, description="Поиск по тексту в резюме, имени или email"),
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Поиск кандидатов по различным критериям"""
    try:
        results = await search_candidates_for_hr(
            session=session,
            skills=skills,
            has_resume=has_resume,
            is_active=is_active,
            is_blocked=is_blocked,
            vacancy_id=vacancy_id,
            min_match_score=min_match_score,
            search_text=search_text,
        )
    except VacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )

    return results


# ==================== АНАЛИЗ ЗАЯВОК ====================

@router.get("/vacancies/{vacancy_id}/applications/analysis", response_model=VacancyApplicationsAnalysis)
async def get_vacancy_applications_analysis(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить детальный анализ всех заявок на вакансию с объяснением соответствия кандидатов"""
    # Проверяем, что вакансия принадлежит текущему HR
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.hr_id == current_user.id
        )
    )
    vacancy = result.scalar_one_or_none()

    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )

    # Получаем все заявки на эту вакансию с информацией о кандидатах
    result = await session.execute(
        select(Application, User)
        .join(User, Application.candidate_id == User.id)
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.desc())
    )

    applications_data = []
    passing_count = 0
    not_passing_count = 0
    without_resume_count = 0

    for application, candidate in result.all():
        match_analysis = None
        error = None

        if not candidate.resume_text:
            without_resume_count += 1
            error = "У кандидата отсутствует резюме, невозможно провести анализ соответствия"
        else:
            # Проводим детальный анализ соответствия
            analysis = analyze_candidate_match(
                resume_text=candidate.resume_text,
                required_skills=vacancy.required_skills
            )
            match_analysis = CandidateMatchAnalysis(**analysis)

            if match_analysis.passes:
                passing_count += 1
            else:
                not_passing_count += 1

        applications_data.append(ApplicationAnalysis(
            application_id=application.id,
            candidate_id=candidate.id,
            candidate_email=candidate.email,
            candidate_full_name=candidate.full_name,
            has_resume=candidate.resume_text is not None,
            application_status=application.status.value,
            match_analysis=match_analysis,
            error=error
        ))

    return VacancyApplicationsAnalysis(
        vacancy_id=vacancy_id,
        vacancy_title=vacancy.title,
        total_applications=len(applications_data),
        passing_candidates=passing_count,
        not_passing_candidates=not_passing_count,
        applications_without_resume=without_resume_count,
        applications=applications_data
    )


# ==================== УВЕДОМЛЕНИЯ ====================

@router.get("/notifications", response_model=list[NotificationRead])
async def get_hr_notifications(
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все уведомления HR-менеджера"""
    notifications = await get_notifications_for_user(
        session=session,
        user=current_user,
    )
    return notifications


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_hr_notification_as_read(
        notification_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Отметить уведомление HR-менеджера как прочитанное"""
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


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        application = await update_application_status_for_hr(
            session=session,
            hr=current_user,
            application_id=application_id,
            new_status=data.status,
        )
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    except AppsVacancyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )
    except VacancyForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    return application

