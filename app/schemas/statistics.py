from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


class UserStatistics(BaseModel):
    total: int = Field(..., description="Общее количество пользователей")
    candidates: int = Field(..., description="Количество кандидатов")
    hr_managers: int = Field(..., description="Количество HR-менеджеров")
    admins: int = Field(..., description="Количество администраторов")
    blocked: int = Field(..., description="Количество заблокированных пользователей")
    with_resume: int = Field(..., description="Количество кандидатов с загруженным резюме")
    verified: int = Field(..., description="Количество верифицированных пользователей")
    active: int = Field(..., description="Количество активных пользователей")


class VacancyStatistics(BaseModel):
    total: int = Field(..., description="Общее количество вакансий")
    active: int = Field(..., description="Количество активных вакансий")
    inactive: int = Field(..., description="Количество неактивных вакансий")
    created_today: int = Field(..., description="Вакансий создано сегодня")
    created_this_week: int = Field(..., description="Вакансий создано на этой неделе")
    created_this_month: int = Field(..., description="Вакансий создано в этом месяце")


class ApplicationStatistics(BaseModel):
    total: int = Field(..., description="Общее количество заявок")
    new: int = Field(..., description="Заявок со статусом 'new'")
    under_review: int = Field(..., description="Заявок со статусом 'under_review'")
    rejected: int = Field(..., description="Заявок со статусом 'rejected'")
    accepted: int = Field(..., description="Заявок со статусом 'accepted'")
    average_match_score: float = Field(..., description="Средний match_score по всем заявкам")
    created_today: int = Field(..., description="Заявок создано сегодня")
    created_this_week: int = Field(..., description="Заявок создано на этой неделе")
    created_this_month: int = Field(..., description="Заявок создано в этом месяце")


class NotificationStatistics(BaseModel):
    total: int = Field(..., description="Общее количество уведомлений")
    unread: int = Field(..., description="Количество непрочитанных уведомлений")
    read: int = Field(..., description="Количество прочитанных уведомлений")
    created_today: int = Field(..., description="Уведомлений создано сегодня")


class PlatformStatistics(BaseModel):
    timestamp: datetime = Field(..., description="Время формирования статистики")
    users: UserStatistics = Field(..., description="Статистика по пользователям")
    vacancies: VacancyStatistics = Field(..., description="Статистика по вакансиям")
    applications: ApplicationStatistics = Field(..., description="Статистика по заявкам")
    notifications: NotificationStatistics = Field(..., description="Статистика по уведомлениям")
    top_skills: List[Dict[str, Any]] = Field(default_factory=list, description="Топ-10 популярных навыков в вакансиях")

