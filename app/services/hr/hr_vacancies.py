from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.user import User
from app.models.vacancy import Vacancy


async def create_vacancy_for_hr(
    session: AsyncSession,
    hr: User,
    data: dict,
) -> Vacancy:
    vacancy = Vacancy(
        **data,
        hr_id=hr.id,
    )
    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


async def get_hr_vacancies(
    session: AsyncSession,
    hr: User,
) -> List[Vacancy]:
    result = await session.execute(
        select(Vacancy).where(Vacancy.hr_id == hr.id)
    )
    return list(result.scalars().all())


async def get_hr_vacancy(
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
        raise NotFoundError(
            message="Vacancy not found",
            code="VACANCY_NOT_FOUND",
            details={"vacancy_id": vacancy_id},
        )
    return vacancy


async def update_hr_vacancy(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
    data: dict,
) -> Vacancy:
    vacancy = await get_hr_vacancy(session=session, hr=hr, vacancy_id=vacancy_id)

    for field, value in data.items():
        setattr(vacancy, field, value)

    await session.commit()
    await session.refresh(vacancy)
    return vacancy


async def delete_hr_vacancy(
    session: AsyncSession,
    hr: User,
    vacancy_id: int,
) -> None:
    vacancy = await get_hr_vacancy(session=session, hr=hr, vacancy_id=vacancy_id)
    await session.delete(vacancy)
    await session.commit()
