from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
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
from app.schemas.vacancy import VacancyRead, VacancyBase, VacancyWithMatchScore
from app.schemas.resume_recommendation import ResumeRecommendation
from app.schemas.platform_rules import PlatformRules, PlatformRule
from app.services.resume_parser import parse_resume
from app.services.match_score import calculate_match_score
from app.services.resume_recommendations import analyze_resume_improvements
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

    # Создаём уведомление для кандидата
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

    # Создаём уведомление для HR-менеджера, если кандидат подходит на вакансию
    if match_score >= 50:
        candidate_name = current_user.full_name if current_user.full_name else current_user.email
        hr_message = f"На вакансию '{vacancy.title}' откликнулся подходящий кандидат: {candidate_name}. Совпадение: {match_score:.0f}%"
        
        hr_notification = Notification(
            user_id=vacancy.hr_id,
            message=hr_message
        )
        session.add(hr_notification)

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


@router.get("/vacancies/recommended", response_model=list[VacancyWithMatchScore])
async def get_recommended_vacancies(
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
        min_score: float = Query(0.0, ge=0.0, le=100.0, description="Минимальный процент совпадения (0-100)"),
):
    """Получить рекомендованные вакансии на основе ключевых слов из резюме"""
    # Проверяем, что у кандидата есть резюме
    if not current_user.resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first to get recommendations"
        )
    
    # Получаем все активные вакансии
    result = await session.execute(
        select(Vacancy).where(Vacancy.is_active == True)
    )
    vacancies = result.scalars().all()
    
    # Рассчитываем match_score для каждой вакансии
    recommended_vacancies = []
    for vacancy in vacancies:
        match_score = calculate_match_score(
            resume_text=current_user.resume_text,
            required_skills=vacancy.required_skills
        )
        
        # Фильтруем по минимальному проценту совпадения
        if match_score >= min_score:
            # Создаем объект с match_score используя модель
            vacancy_with_score = VacancyWithMatchScore(
                id=vacancy.id,
                title=vacancy.title,
                description=vacancy.description,
                required_skills=vacancy.required_skills,
                hr_id=vacancy.hr_id,
                is_active=vacancy.is_active,
                created_at=vacancy.created_at,
                updated_at=vacancy.updated_at,
                match_score=match_score
            )
            recommended_vacancies.append(vacancy_with_score)
    
    # Сортируем по match_score по убыванию
    recommended_vacancies.sort(key=lambda x: x.match_score, reverse=True)
    
    return recommended_vacancies


@router.get("/resume/recommendations", response_model=ResumeRecommendation)
async def get_resume_recommendations(
        current_user: User = Depends(get_current_candidate),
        session: AsyncSession = Depends(get_async_session),
):
    """Получить рекомендации по улучшению резюме на основе анализа популярных навыков в вакансиях"""
    # Проверяем, что у кандидата есть резюме
    if not current_user.resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload your resume first to get recommendations"
        )
    
    # Получаем все активные вакансии
    result = await session.execute(
        select(Vacancy).where(Vacancy.is_active == True)
    )
    vacancies = result.scalars().all()
    
    if not vacancies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active vacancies found for analysis"
        )
    
    # Собираем все навыки из вакансий
    all_vacancy_skills = [vacancy.required_skills for vacancy in vacancies]
    
    # Анализируем резюме и генерируем рекомендации
    recommendations_data = analyze_resume_improvements(
        resume_text=current_user.resume_text,
        all_vacancy_skills=all_vacancy_skills
    )
    
    return recommendations_data


@router.get("/platform-rules", response_model=PlatformRules)
async def get_platform_rules():
    """Получить правила использования платформы для кандидатов"""
    from datetime import datetime
    
    rules = [
        PlatformRule(
            title="Регистрация и профиль",
            description="При регистрации вы должны предоставить достоверную информацию. Укажите корректное ФИО в формате 'Фамилия Имя Отчество' и действительный email адрес. Обновляйте свой профиль при изменении данных."
        ),
        PlatformRule(
            title="Загрузка резюме",
            description="Вы обязаны загрузить актуальное резюме в формате DOCX или PDF. Резюме должно содержать полную информацию о вашем опыте работы, навыках и образовании. Регулярно обновляйте резюме при получении нового опыта."
        ),
        PlatformRule(
            title="Подача заявок на вакансии",
            description="Вы можете подавать заявку на любую открытую вакансию, но только один раз на каждую вакансию. Перед подачей заявки убедитесь, что ваше резюме актуально и соответствует требованиям вакансии."
        ),
        PlatformRule(
            title="Поведение на платформе",
            description="Запрещается публиковать недостоверную информацию, спамить работодателей или использовать платформу для мошеннических целей. Уважайте права других пользователей и соблюдайте этические нормы общения."
        ),
        PlatformRule(
            title="Конфиденциальность",
            description="Ваши личные данные и резюме доступны только работодателям, на вакансии которых вы подали заявку, и администраторам платформы. Мы не передаем ваши данные третьим лицам без вашего согласия."
        ),
        PlatformRule(
            title="Ответственность за информацию",
            description="Вы несете полную ответственность за достоверность предоставленной информации. Предоставление ложных данных может привести к блокировке аккаунта и исключению из платформы."
        ),
        PlatformRule(
            title="Блокировка аккаунта",
            description="Администратор имеет право заблокировать ваш аккаунт в случае нарушения правил платформы, предоставления недостоверной информации или иных действий, наносящих вред платформе или другим пользователям."
        ),
        PlatformRule(
            title="Рекомендации и улучшение резюме",
            description="Используйте рекомендации по улучшению резюме для повышения ваших шансов на трудоустройство. Система анализирует популярные навыки в вакансиях и предлагает способы улучшить ваше резюме."
        ),
        PlatformRule(
            title="Уведомления",
            description="Вы будете получать уведомления о статусе ваших заявок и других важных событиях. Регулярно проверяйте уведомления, чтобы быть в курсе изменений."
        ),
        PlatformRule(
            title="Контакты и поддержка",
            description="При возникновении вопросов или проблем обратитесь к администратору платформы через указанные контактные данные. Мы постараемся помочь вам в кратчайшие сроки."
        )
    ]
    
    return PlatformRules(
        rules=rules,
        last_updated=datetime.now().isoformat()
    )
