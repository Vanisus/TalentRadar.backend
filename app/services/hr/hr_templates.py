from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.user import User
from app.models.vacancy import Vacancy
from app.models.vacancy_template import VacancyTemplate
from app.schemas.vacancy import VacancyFromTemplate


async def create_template_for_hr(
    session: AsyncSession,
    hr: User,
    data: dict,
) -> VacancyTemplate:
    template = VacancyTemplate(
        **data,
        hr_id=hr.id,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def get_hr_templates(
    session: AsyncSession,
    hr: User,
) -> List[VacancyTemplate]:
    result = await session.execute(
        select(VacancyTemplate).where(VacancyTemplate.hr_id == hr.id)
    )
    return list(result.scalars().all())


async def get_hr_template(
    session: AsyncSession,
    hr: User,
    template_id: int,
) -> VacancyTemplate:
    result = await session.execute(
        select(VacancyTemplate).where(
            VacancyTemplate.id == template_id,
            VacancyTemplate.hr_id == hr.id,
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFoundError(
            message="Template not found",
            code="TEMPLATE_NOT_FOUND",
            details={"template_id": template_id},
        )
    return template


async def update_hr_template(
    session: AsyncSession,
    hr: User,
    template_id: int,
    data: dict,
) -> VacancyTemplate:
    template = await get_hr_template(session=session, hr=hr, template_id=template_id)

    for field, value in data.items():
        setattr(template, field, value)

    await session.commit()
    await session.refresh(template)
    return template


async def delete_hr_template(
    session: AsyncSession,
    hr: User,
    template_id: int,
) -> None:
    template = await get_hr_template(session=session, hr=hr, template_id=template_id)
    await session.delete(template)
    await session.commit()


async def create_vacancy_from_template_for_hr(
    session: AsyncSession,
    hr: User,
    template_id: int,
    vacancy_data: VacancyFromTemplate,
) -> Vacancy:
    template = await get_hr_template(session=session, hr=hr, template_id=template_id)

    vacancy_title = vacancy_data.title or template.title
    vacancy_description = vacancy_data.description or template.description
    vacancy_skills = vacancy_data.required_skills or template.required_skills

    vacancy = Vacancy(
        title=vacancy_title,
        description=vacancy_description,
        required_skills=vacancy_skills,
        hr_id=hr.id,
        is_active=vacancy_data.is_active,
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy
