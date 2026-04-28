from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.models.application import Application, ApplicationStatus
from app.models.user import User
from app.models.user import User as CandidateUser
from app.schemas.application import ApplicationStatusUpdate, ApplicationRead, ApplicationHRRead
from app.schemas.candidate_analysis import (
    VacancyApplicationsAnalysis,
    ApplicationAnalysis,
    CandidateMatchAnalysis,
)
from app.schemas.candidate_search import CandidateSearchResult
from app.schemas.hr_saved_search import SavedSearchCreate, SavedSearchRead
from app.schemas.notification import NotificationRead
from app.schemas.vacancy import (
    VacancyCreate,
    VacancyRead,
    VacancyUpdate,
    VacancyFromTemplate,
)
from app.services.hr.hr_dashboard import get_hr_dashboard
from app.schemas.vacancy_template import (
    VacancyTemplateCreate,
    VacancyTemplateRead,
    VacancyTemplateUpdate,
)
from app.services.analytics.hr_analytics import get_vacancy_analytics_for_hr
from app.services.candidate.candidate_analysis import analyze_candidate_match
from app.services.hr.hr_applications import (
    get_vacancy_applications_for_hr,
    update_application_status_for_hr, get_all_applications_for_hr,
)
from app.services.hr.hr_saved_searches import (
    create_saved_search_for_hr,
    list_saved_searches_for_hr,
    delete_saved_search_for_hr, get_saved_search_for_hr,
)
from app.services.hr.hr_search import get_hr_vacancy_with_stats, search_candidates_for_hr
from app.services.hr.hr_templates import (
    create_template_for_hr,
    get_hr_templates,
    get_hr_template,
    update_hr_template,
    delete_hr_template,
    create_vacancy_from_template_for_hr,
)
from app.services.hr.hr_vacancies import (
    create_vacancy_for_hr,
    get_hr_vacancies,
    get_hr_vacancy,
    update_hr_vacancy,
    delete_hr_vacancy,
)
from app.services.notifications.notifications import (
    get_notifications_for_user,
    mark_notification_as_read_for_user,
)

from app.services.llm.application_analysis import analyze_application_with_llm


router = APIRouter(prefix="/hr", tags=["HR"])


# ==================== CRUD вакансий ====================

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


@router.get("/vacancies", response_model=List[VacancyRead])
async def get_my_vacancies(
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_hr_vacancies(
        session=session,
        hr=current_user,
    )


@router.get("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def get_vacancy(
    vacancy_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_hr_vacancy(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
    )


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def update_vacancy(
    vacancy_id: int,
    vacancy_data: VacancyUpdate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_hr_vacancy(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
        data=vacancy_data.model_dump(exclude_unset=True),
    )


@router.delete("/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_hr_vacancy(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
    )


# ==================== Заявки на вакансию ====================

@router.get("/vacancies/{vacancy_id}/applications")
async def get_vacancy_applications(
    vacancy_id: int,
    min_score: float = Query(0, ge=0, le=100, description="Минимальный match_score"),
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_vacancy_applications_for_hr(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
        min_score=min_score,
    )


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    application = await update_application_status_for_hr(
        session=session,
        hr=current_user,
        application_id=application_id,
        new_status=data.status,
    )
    return application


@router.get("/applications", response_model=List[ApplicationHRRead])
async def get_all_applications(
    status: Optional[ApplicationStatus] = Query(
        None,
        description="Фильтр по статусу (pending, under_review, accepted, rejected)",
    ),
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Все отклики по всем вакансиям текущего HR.
    Опционально фильтровать по статусу.
    """
    return await get_all_applications_for_hr(
        session=session,
        hr=current_user,
        status=status,
    )



# ==================== Аналитика ====================

@router.get("/vacancies/{vacancy_id}/analytics")
async def get_vacancy_analytics(
    vacancy_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    data = await get_vacancy_analytics_for_hr(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
    )

    return data


# ==================== Шаблоны вакансий ====================

@router.post("/templates", response_model=VacancyTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: VacancyTemplateCreate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await create_template_for_hr(
        session=session,
        hr=current_user,
        data=template_data.model_dump(),
    )


@router.get("/templates", response_model=List[VacancyTemplateRead])
async def get_my_templates(
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_hr_templates(
        session=session,
        hr=current_user,
    )


@router.get("/templates/{template_id}", response_model=VacancyTemplateRead)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_hr_template(
        session=session,
        hr=current_user,
        template_id=template_id,
    )


@router.patch("/templates/{template_id}", response_model=VacancyTemplateRead)
async def update_template(
    template_id: int,
    template_data: VacancyTemplateUpdate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_hr_template(
        session=session,
        hr=current_user,
        template_id=template_id,
        data=template_data.model_dump(exclude_unset=True),
    )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_hr_template(
        session=session,
        hr=current_user,
        template_id=template_id,
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
    return await create_vacancy_from_template_for_hr(
        session=session,
        hr=current_user,
        template_id=template_id,
        vacancy_data=vacancy_data,
    )


# ==================== Поиск кандидатов ====================

@router.get("/candidates/search", response_model=List[CandidateSearchResult])
async def search_candidates(
    skills: Optional[List[str]] = Query(None, description="Список навыков для поиска в резюме"),
    has_resume: Optional[bool] = Query(None, description="Только кандидаты с загруженным резюме"),
    is_active: Optional[bool] = Query(None, description="Только активные кандидаты"),
    is_blocked: Optional[bool] = Query(
        False,
        description="Только заблокированные кандидаты (по умолчанию False)",
    ),
    vacancy_id: Optional[int] = Query(
        None,
        description="ID вакансии для расчета match_score",
    ),
    min_match_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=100.0,
        description="Минимальный match_score с указанной вакансией",
    ),
    search_text: Optional[str] = Query(
        None,
        description="Поиск по тексту в резюме, имени или email",
    ),
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await search_candidates_for_hr(
        session=session,
        skills=skills,
        has_resume=has_resume,
        is_active=is_active,
        is_blocked=is_blocked,
        vacancy_id=vacancy_id,
        min_match_score=min_match_score,
        search_text=search_text,
    )


# ==================== Анализ заявок ====================

@router.get(
    "/vacancies/{vacancy_id}/applications/analysis",
    response_model=VacancyApplicationsAnalysis,
)
async def get_vacancy_applications_analysis(
    vacancy_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    # Проверяем владение вакансией через сервис
    vacancy_stats = await get_hr_vacancy_with_stats(
        session=session,
        hr=current_user,
        vacancy_id=vacancy_id,
    )

    result = await session.execute(
        select(Application, CandidateUser)
        .join(CandidateUser, Application.candidate_id == CandidateUser.id)
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.desc())
    )

    applications_data: List[ApplicationAnalysis] = []
    passing_count = 0
    not_passing_count = 0
    without_resume_count = 0

    for application, candidate in result.all():
        match_analysis = None
        error = None

        if not candidate.resume_text:
            without_resume_count += 1
            error = (
                "У кандидата отсутствует резюме, невозможно провести анализ соответствия"
            )
        else:
            analysis = analyze_candidate_match(
                resume_text=candidate.resume_text,
                required_skills=vacancy_stats["required_skills"]
                if "required_skills" in vacancy_stats
                else [],
            )
            match_analysis = CandidateMatchAnalysis(**analysis)

            if match_analysis.passes:
                passing_count += 1
            else:
                not_passing_count += 1

        applications_data.append(
            ApplicationAnalysis(
                application_id=application.id,
                candidate_id=candidate.id,
                candidate_email=candidate.email,
                candidate_full_name=candidate.full_name,
                has_resume=candidate.resume_text is not None,
                application_status=application.status.value,
                match_analysis=match_analysis,
                error=error,
            )
        )

    return VacancyApplicationsAnalysis(
        vacancy_id=vacancy_id,
        vacancy_title=vacancy_stats["title"],
        total_applications=len(applications_data),
        passing_candidates=passing_count,
        not_passing_candidates=not_passing_count,
        applications_without_resume=without_resume_count,
        applications=applications_data,
    )


# ==================== Уведомления ====================

@router.get("/notifications", response_model=List[NotificationRead])
async def get_hr_notifications(
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_notifications_for_user(
        session=session,
        user=current_user,
    )


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_hr_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await mark_notification_as_read_for_user(
        session=session,
        user=current_user,
        notification_id=notification_id,
    )

# ==================== Сохранённые поиски кандидатов ====================

@router.get(
    "/candidates/searches",
    response_model=list[SavedSearchRead],
)
async def list_saved_candidate_searches(
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_saved_searches_for_hr(
        session=session,
        hr=current_user,
    )


@router.post(
    "/candidates/searches",
    response_model=SavedSearchRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_saved_candidate_search(
    body: SavedSearchCreate,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    saved = await create_saved_search_for_hr(
        session=session,
        hr=current_user,
        name=body.name,
        params=body.params,
    )
    return saved


@router.delete(
    "/candidates/searches/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_saved_candidate_search(
    search_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_saved_search_for_hr(
        session=session,
        hr=current_user,
        search_id=search_id,
    )


@router.get(
    "/candidates/searches/{search_id}/run",
    response_model=list[CandidateSearchResult],
)
async def run_saved_candidate_search(
    search_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    saved = await get_saved_search_for_hr(
        session=session,
        hr=current_user,
        search_id=search_id,
    )

    return await search_candidates_for_hr(
        session=session,
        **saved.params,
    )

@router.get("/dashboard")
async def get_hr_dashboard_view(
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
    days_new: int = 1,
    days_stale: int = 7,
):
    """
    Рабочий экран HR:
    - новые отклики за последние days_new дней
    - непрочитанные уведомления
    - вакансии без откликов / с устаревшими откликами за days_stale дней
    """
    return await get_hr_dashboard(
        session=session,
        hr=current_user,
        days_new=days_new,
        days_stale=days_stale,
    )

@router.post("/applications/{application_id}/llm-analyze")
async def llm_analyze_application(
    application_id: int,
    current_user: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Запустить LLM-анализ конкретной заявки.
    Результат — сохраняется в match_summary и (опционально) обновляет match_score.
    """
    return await analyze_application_with_llm(
        session=session,
        hr=current_user,
        application_id=application_id,
    )
