from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.notification import Notification
from app.models.user import User
from app.models.vacancy import Vacancy


class ApplicationNotFoundError(Exception):
    pass


class VacancyNotFoundError(Exception):
    pass


class VacancyForbiddenError(Exception):
    pass


async def ensure_hr_vacancy(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> Vacancy:
    result = await session.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.hr_id == hr.id,
        )
    )
    vacancy = result.scalar_one_or_none()
    if vacancy is None:
        raise VacancyNotFoundError()
    return vacancy


async def get_vacancy_applications_for_hr(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
    min_score: float = 0,
) -> Dict[str, Any]:
    vacancy = await ensure_hr_vacancy(session=session, hr=hr, vacancy_id=vacancy_id)

    result = await session.execute(
        select(Application, User)
        .join(User, Application.candidate_id == User.id)
        .where(
            Application.vacancy_id == vacancy_id,
            Application.match_score >= min_score,
        )
        .order_by(Application.match_score.desc())
    )

    applications_data: List[Dict[str, Any]] = []
    for application, candidate in result.all():
        applications_data.append(
            {
                "id": application.id,
                "candidate_email": candidate.email,
                "candidate_id": candidate.id,
                "candidate_full_name": candidate.full_name,
                "status": application.status.value,
                "match_score": application.match_score,
                "created_at": application.created_at,
                "updated_at": application.updated_at,
                "resume_path": candidate.resume_path,
            }
        )

    return {
        "vacancy_id": vacancy.id,
        "vacancy_title": vacancy.title,
        "total_applications": len(applications_data),
        "applications": applications_data,
    }


async def update_application_status_for_hr(
    session: AsyncSession,
    hr: User,
    application_id: int,
    new_status: ApplicationStatus,
) -> Application:
    # 1) Находим application
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise ApplicationNotFoundError()

    # 2) Проверяем, что вакансия принадлежит HR
    result = await session.execute(
        select(Vacancy).where(Vacancy.id == application.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()
    if vacancy is None:
        raise VacancyNotFoundError()
    if vacancy.hr_id != hr.id:
        raise VacancyForbiddenError()

    # 3) Меняем статус
    application.status = new_status
    await session.commit()
    await session.refresh(application)

    # 4) Уведомление кандидату
    if new_status == ApplicationStatus.ACCEPTED:
        msg = f"Вас пригласили на скрининг по вакансии '{vacancy.title}'."
    elif new_status == ApplicationStatus.REJECTED:
        msg = f"К сожалению, вам отказано по вакансии '{vacancy.title}'."
    elif new_status == ApplicationStatus.UNDER_REVIEW:
        msg = f"Ваш отклик на вакансию '{vacancy.title}' взят в работу HR."
    else:
        msg = f"Статус отклика на вакансию '{vacancy.title}' обновлён: {new_status.value}."

    session.add(Notification(user_id=application.candidate_id, message=msg))
    await session.commit()

    return application
