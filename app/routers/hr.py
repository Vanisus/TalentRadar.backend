from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.models.user import User, UserRole
from app.models.vacancy import Vacancy
from app.models.vacancy_template import VacancyTemplate
from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.schemas.vacancy import VacancyCreate, VacancyRead, VacancyUpdate, VacancyFromTemplate
from app.schemas.vacancy_template import VacancyTemplateCreate, VacancyTemplateRead, VacancyTemplateUpdate
from app.schemas.candidate_search import CandidateSearchFilters, CandidateSearchResult
from app.schemas.candidate_analysis import VacancyApplicationsAnalysis, ApplicationAnalysis, CandidateMatchAnalysis
from app.schemas.notification import NotificationRead
from app.services.match_score import calculate_match_score
from app.services.candidate_analysis import analyze_candidate_match
from app.schemas.application import ApplicationStatusUpdate, ApplicationRead

router = APIRouter(prefix="/hr", tags=["HR"])


# ==================== CRUD ВАКАНСИЙ ====================

@router.post("/vacancies", response_model=VacancyRead, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
        vacancy_data: VacancyCreate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Создание новой вакансии (только для HR)"""
    vacancy = Vacancy(
        **vacancy_data.model_dump(),
        hr_id=current_user.id
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


@router.get("/vacancies", response_model=list[VacancyRead])
async def get_my_vacancies(
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все вакансии текущего HR-менеджера"""
    result = await session.execute(
        select(Vacancy).where(Vacancy.hr_id == current_user.id)
    )
    vacancies = result.scalars().all()
    return vacancies


@router.get("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def get_vacancy(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить конкретную вакансию"""
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

    return vacancy


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyRead)
async def update_vacancy(
        vacancy_id: int,
        vacancy_data: VacancyUpdate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Обновление вакансии"""
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

    # Обновляем только переданные поля
    for field, value in vacancy_data.model_dump(exclude_unset=True).items():
        setattr(vacancy, field, value)

    await session.commit()
    await session.refresh(vacancy)
    return vacancy


@router.delete("/vacancies/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Удаление вакансии"""
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

    await session.delete(vacancy)
    await session.commit()


# ==================== ЗАЯВКИ НА ВАКАНСИЮ ====================

@router.get("/vacancies/{vacancy_id}/applications")
async def get_vacancy_applications(
        vacancy_id: int,
        min_score: float = Query(0, ge=0, le=100, description="Минимальный match_score"),
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить заявки на вакансию с фильтром по match_score"""
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

    # Получаем заявки с кандидатами
    result = await session.execute(
        select(Application, User)
        .join(User, Application.candidate_id == User.id)
        .where(
            Application.vacancy_id == vacancy_id,
            Application.match_score >= min_score
        )
        .order_by(Application.match_score.desc())
    )

    applications_data = []
    for application, candidate in result.all():
        applications_data.append({
            "id": application.id,
            "candidate_email": candidate.email,
            "candidate_id": candidate.id,
            "candidate_full_name": candidate.full_name,
            "status": application.status.value,
            "match_score": application.match_score,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "resume_path": candidate.resume_path,
        })

    return {
        "vacancy_id": vacancy_id,
        "vacancy_title": vacancy.title,
        "total_applications": len(applications_data),
        "applications": applications_data
    }


# ==================== АНАЛИТИКА ====================

@router.get("/vacancies/{vacancy_id}/analytics")
async def get_vacancy_analytics(
        vacancy_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить аналитику по вакансии"""
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

    # Общее количество откликов
    total_applications = await session.execute(
        select(func.count(Application.id))
        .where(Application.vacancy_id == vacancy_id)
    )
    total_count = total_applications.scalar()

    # Средний match_score
    avg_score = await session.execute(
        select(func.avg(Application.match_score))
        .where(Application.vacancy_id == vacancy_id)
    )
    average_match_score = avg_score.scalar() or 0.0

    # Распределение по статусам
    status_distribution = await session.execute(
        select(
            Application.status,
            func.count(Application.id)
        )
        .where(Application.vacancy_id == vacancy_id)
        .group_by(Application.status)
    )

    status_counts = {
        "new": 0,
        "under_review": 0,
        "rejected": 0,
        "accepted": 0
    }

    for status, count in status_distribution.all():
        status_counts[status.value] = count

    # Время до первого отклика
    first_application = await session.execute(
        select(Application.created_at)
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.asc())
        .limit(1)
    )
    first_app_time = first_application.scalar()

    time_to_first_response = None
    if first_app_time:
        delta = first_app_time - vacancy.created_at
        time_to_first_response = {
            "days": delta.days,
            "hours": delta.seconds // 3600,
            "minutes": (delta.seconds % 3600) // 60,
            "total_seconds": int(delta.total_seconds())
        }

    return {
        "vacancy_id": vacancy_id,
        "vacancy_title": vacancy.title,
        "vacancy_created_at": vacancy.created_at,
        "is_active": vacancy.is_active,
        "statistics": {
            "total_applications": total_count,
            "average_match_score": round(float(average_match_score), 2),
            "status_distribution": status_counts,
            "time_to_first_response": time_to_first_response
        }
    }


# ==================== ШАБЛОНЫ ВАКАНСИЙ ====================

@router.post("/templates", response_model=VacancyTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
        template_data: VacancyTemplateCreate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Создание нового шаблона вакансии"""
    template = VacancyTemplate(
        **template_data.model_dump(),
        hr_id=current_user.id
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@router.get("/templates", response_model=list[VacancyTemplateRead])
async def get_my_templates(
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все шаблоны текущего HR-менеджера"""
    result = await session.execute(
        select(VacancyTemplate).where(VacancyTemplate.hr_id == current_user.id)
    )
    templates = result.scalars().all()
    return templates


@router.get("/templates/{template_id}", response_model=VacancyTemplateRead)
async def get_template(
        template_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить конкретный шаблон"""
    result = await session.execute(
        select(VacancyTemplate).where(
            VacancyTemplate.id == template_id,
            VacancyTemplate.hr_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
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
    result = await session.execute(
        select(VacancyTemplate).where(
            VacancyTemplate.id == template_id,
            VacancyTemplate.hr_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Обновляем только переданные поля
    for field, value in template_data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await session.commit()
    await session.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
        template_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Удаление шаблона вакансии"""
    result = await session.execute(
        select(VacancyTemplate).where(
            VacancyTemplate.id == template_id,
            VacancyTemplate.hr_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    await session.delete(template)
    await session.commit()


@router.post("/templates/{template_id}/create-vacancy", response_model=VacancyRead, status_code=status.HTTP_201_CREATED)
async def create_vacancy_from_template(
        template_id: int,
        vacancy_data: VacancyFromTemplate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Создать вакансию из шаблона"""
    # Получаем шаблон
    result = await session.execute(
        select(VacancyTemplate).where(
            VacancyTemplate.id == template_id,
            VacancyTemplate.hr_id == current_user.id
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Используем данные из шаблона, перезаписывая их данными из vacancy_data, если они указаны
    vacancy_title = vacancy_data.title if vacancy_data.title else template.title
    vacancy_description = vacancy_data.description if vacancy_data.description else template.description
    vacancy_skills = vacancy_data.required_skills if vacancy_data.required_skills else template.required_skills

    # Создаем вакансию
    vacancy = Vacancy(
        title=vacancy_title,
        description=vacancy_description,
        required_skills=vacancy_skills,
        hr_id=current_user.id,
        is_active=vacancy_data.is_active
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


# ==================== ПОИСК КАНДИДАТОВ ====================

@router.get("/candidates/search", response_model=list[CandidateSearchResult])
async def search_candidates(
        skills: Optional[list[str]] = Query(None, description="Список навыков для поиска в резюме"),
        has_resume: Optional[bool] = Query(None, description="Только кандидаты с загруженным резюме"),
        is_active: Optional[bool] = Query(None, description="Только активные кандидаты"),
        is_blocked: Optional[bool] = Query(False, description="Только заблокированные кандидаты (по умолчанию False)"),
        vacancy_id: Optional[int] = Query(None, description="ID вакансии для расчета match_score"),
        min_match_score: Optional[float] = Query(None, ge=0.0, le=100.0,
                                                 description="Минимальный match_score с указанной вакансией"),
        search_text: Optional[str] = Query(None, description="Поиск по тексту в резюме, имени или email"),
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Поиск кандидатов по различным критериям"""
    # Начинаем с базового запроса - только кандидаты
    query = select(User).where(User.role == UserRole.CANDIDATE)

    # Фильтр по наличию резюме
    if has_resume is not None:
        if has_resume:
            query = query.where(User.resume_text.isnot(None))
        else:
            query = query.where(User.resume_text.is_(None))

    # Фильтр по активности
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Фильтр по блокировке
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)

    # Поиск по тексту (в резюме, имени или email)
    if search_text:
        search_lower = search_text.lower()
        # SQLAlchemy автоматически обрабатывает NULL значения в условиях or_
        query = query.where(
            or_(
                func.lower(User.email).contains(search_lower),
                func.lower(User.full_name).contains(search_lower),
                func.lower(User.resume_text).contains(search_lower)
            )
        )

    # Выполняем запрос
    result = await session.execute(query)
    candidates = result.scalars().all()

    # Получаем вакансию для расчета match_score, если указана
    vacancy = None
    if vacancy_id:
        vacancy_result = await session.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vacancy not found"
            )

    # Фильтруем по навыкам и рассчитываем match_score
    results = []
    for candidate in candidates:
        # Фильтр по навыкам (если указаны)
        if skills:
            if not candidate.resume_text:
                continue  # Пропускаем кандидатов без резюме, если требуются навыки

            resume_lower = candidate.resume_text.lower()
            has_any_skill = any(skill.lower() in resume_lower for skill in skills)
            if not has_any_skill:
                continue  # Пропускаем кандидатов без требуемых навыков

        # Рассчитываем match_score, если указана вакансия
        match_score = None
        if vacancy and candidate.resume_text:
            match_score = calculate_match_score(
                resume_text=candidate.resume_text,
                required_skills=vacancy.required_skills
            )

            # Фильтруем по минимальному match_score
            if min_match_score is not None and match_score < min_match_score:
                continue  # Пропускаем кандидатов с низким match_score

        # Получаем предпросмотр резюме
        resume_preview = None
        if candidate.resume_text:
            preview_length = 200
            resume_preview = candidate.resume_text[:preview_length]
            if len(candidate.resume_text) > preview_length:
                resume_preview += "..."

        results.append(CandidateSearchResult(
            id=candidate.id,
            email=candidate.email,
            full_name=candidate.full_name,
            has_resume=candidate.resume_text is not None,
            is_active=candidate.is_active,
            is_blocked=candidate.is_blocked,
            match_score=match_score,
            resume_preview=resume_preview
        ))

    # Сортируем по match_score, если он был рассчитан
    if vacancy_id:
        results.sort(key=lambda x: x.match_score if x.match_score is not None else 0.0, reverse=True)
    else:
        # Иначе сортируем по email
        results.sort(key=lambda x: x.email)

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
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return notifications


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_hr_notification_as_read(
        notification_id: int,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    """Отметить уведомление HR-менеджера как прочитанное"""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True
    await session.commit()


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
async def update_application_status(
        application_id: int,
        data: ApplicationStatusUpdate,
        current_user: User = Depends(get_current_hr),
        session: AsyncSession = Depends(get_async_session),
):
    # 1) Находим application
    result = await session.execute(select(Application).where(Application.id == application_id))
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # 2) Проверяем, что вакансия принадлежит HR
    result = await session.execute(select(Vacancy).where(Vacancy.id == application.vacancy_id))
    vacancy = result.scalar_one_or_none()
    if not vacancy or vacancy.hr_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 3) Меняем статус
    application.status = data.status
    await session.commit()
    await session.refresh(application)

    # 4) Уведомление кандидату
    if data.status == ApplicationStatus.ACCEPTED:
        msg = f"Вас пригласили на скрининг по вакансии '{vacancy.title}'."
    elif data.status == ApplicationStatus.REJECTED:
        msg = f"К сожалению, вам отказано по вакансии '{vacancy.title}'."
    elif data.status == ApplicationStatus.UNDER_REVIEW:
        msg = f"Ваш отклик на вакансию '{vacancy.title}' взят в работу HR."
    else:
        msg = f"Статус отклика на вакансию '{vacancy.title}' обновлён: {data.status.value}."

    session.add(Notification(user_id=application.candidate_id, message=msg))
    await session.commit()

    return application
