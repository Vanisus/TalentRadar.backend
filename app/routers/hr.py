from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.models.user import User
from app.models.vacancy import Vacancy
from app.models.application import Application
from app.schemas.vacancy import VacancyCreate, VacancyRead, VacancyUpdate

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
            "status": application.status.value,
            "match_score": application.match_score,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "resume_path": candidate.resume_path
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
