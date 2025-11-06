from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil

from app.database import get_async_session
from app.dependencies import get_current_candidate
from app.models.user import User
from app.models.vacancy import Vacancy
from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.schemas.notification import NotificationRead
from app.schemas.vacancy import VacancyRead, VacancyBase
from app.services.resume_parser import parse_resume
from app.services.match_score import calculate_match_score
from app.config import settings

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("/resume", status_code=status.HTTP_200_OK)
async def upload_resume(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
):
    """Загрузка резюме (docx или pdf)"""
    # Проверка расширения файла
    allowed_extensions = [".docx", ".pdf"]
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {', '.join(allowed_extensions)} files are allowed"
        )

    # Создаём папку uploads если её нет
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем файл
    file_path = upload_dir / f"user_{current_user.id}_{file.filename}"

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Парсим резюме
    resume_text = parse_resume(str(file_path))

    # Обновляем пользователя
    current_user.resume_path = str(file_path)
    current_user.resume_text = resume_text

    await session.commit()

    return {
        "message": "Resume uploaded successfully",
        "file_path": str(file_path),
        "extracted_text_length": len(resume_text)
    }


@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
        application_data: ApplicationCreate,
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
):
    """Подача заявки на вакансию"""
    # Проверяем, что вакансия существует
    result = await session.execute(
        select(Vacancy).where(Vacancy.id == application_data.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()

    if not vacancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found"
        )

    if not vacancy.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vacancy is not active"
        )

    # Проверяем на дубли
    result = await session.execute(
        select(Application).where(
            Application.vacancy_id == application_data.vacancy_id,
            Application.candidate_id == current_user.id
        )
    )
    existing_application = result.scalar_one_or_none()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this vacancy"
        )

    # Проверяем, что у кандидата есть резюме
    if not current_user.resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first"
        )

    # Рассчитываем match_score
    match_score = calculate_match_score(
        resume_text=current_user.resume_text,
        required_skills=vacancy.required_skills
    )

    # Создаём заявку
    application = Application(
        vacancy_id=application_data.vacancy_id,
        candidate_id=current_user.id,
        match_score=match_score
    )
    session.add(application)

    # Создаём уведомление
    if match_score >= 70:
        message = f"Отлично! Вы подходите на вакансию '{vacancy.title}' на {match_score:.0f}%"
    elif match_score >= 50:
        message = f"Вы подходите на вакансию '{vacancy.title}' на {match_score:.0f}%"
    else:
        message = f"К сожалению, ваш профиль соответствует вакансии '{vacancy.title}' только на {match_score:.0f}%"

    notification = Notification(
        user_id=current_user.id,
        message=message
    )
    session.add(notification)

    await session.commit()
    await session.refresh(application)

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
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return notifications


@router.patch("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_as_read(
        notification_id: int,
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
):
    """Отметить уведомление как прочитанное"""
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


@router.get("/vacancies", response_model=list[VacancyRead])
async def get_open_vacancies(
        session: AsyncSession = Depends(get_async_session),
):
    """Получить все открытые вакансии (is_active=True)"""
    result = await session.execute(
        select(Vacancy).where(Vacancy.is_active == True)
    )
    vacancies = result.scalars().all()
    return vacancies
