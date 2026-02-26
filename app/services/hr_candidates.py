from datetime import date
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.candidate_note import CandidateNote
from app.models.candidate_profile import CandidateProfile, WorkExperience, PortfolioItem, CandidateSkill
from app.models.user import User
from app.schemas.hr_candidate import HRCandidateShort, HRCandidateProfile


def _calc_total_experience_years(experiences: list[WorkExperience]) -> float:
    total_days = 0
    today = date.today()

    for exp in experiences:
        if not exp.start_date:
            continue
        start = exp.start_date
        end = exp.end_date or today
        total_days += (end - start).days

    return round(total_days / 365, 1) if total_days > 0 else 0.0


async def get_hr_candidate_profile(
    session: AsyncSession,
    user_id: int,
) -> Optional[HRCandidateProfile]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.profile)
            .selectinload(CandidateProfile.experiences),
            selectinload(User.profile)
            .selectinload(CandidateProfile.educations),
            selectinload(User.profile)
            .selectinload(CandidateProfile.skills),
            selectinload(User.profile)
            .selectinload(CandidateProfile.certificates),
            selectinload(User.profile)
            .selectinload(CandidateProfile.portfolio_items),
        )
        .where(User.id == user_id)
    )
    user: User | None = result.scalar_one_or_none()
    if user is None or user.profile is None:
        return None

    profile = user.profile

    return HRCandidateProfile(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=profile.phone,
        telegram=profile.telegram,
        city=profile.city,
        desired_position=profile.desired_position,
        desired_salary=profile.desired_salary,
        about_me=profile.about_me,
        birth_date=profile.birth_date,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        experiences=list(profile.experiences),
        educations=list(profile.educations),
        skills=list(profile.skills),
        certificates=list(profile.certificates),
        portfolio_items=list(profile.portfolio_items),
    )


async def list_hr_candidates(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    city: str | None = None,
    min_experience: float | None = None,
    has_portfolio: bool | None = None,
    skill: str | None = None,
) -> List[HRCandidateShort]:
    """
    Список кандидатов для HR с краткой карточкой и простыми фильтрами.
    """
    query = (
        select(User)
        .join(CandidateProfile, CandidateProfile.user_id == User.id)
        .options(
            selectinload(User.profile).selectinload(CandidateProfile.experiences),
            selectinload(User.profile).selectinload(CandidateProfile.portfolio_items),
            selectinload(User.profile).selectinload(CandidateProfile.skills),
        )
        .order_by(User.id.desc())
    )

    if city:
        query = query.where(func.lower(CandidateProfile.city) == city.lower())

    if has_portfolio is True:
        query = query.where(
            func.array_length(
                func.coalesce(
                    func.array_agg(PortfolioItem.id).filter(
                        PortfolioItem.profile_id == CandidateProfile.id
                    ),
                    "{}"
                ),
                1,
            )
            > 0
        )

    if skill:
        # упрощённо: просто джоин по таблице навыков и фильтр по ILIKE
        query = (
            query.join(
                CandidateSkill,
                CandidateSkill.profile_id == CandidateProfile.id,
            )
            .where(func.lower(CandidateSkill.name).like(f"%{skill.lower()}%"))
        )

    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    users = list(result.scalars().unique().all())

    candidates: List[HRCandidateShort] = []
    for user in users:
        profile = user.profile
        total_experience = _calc_total_experience_years(profile.experiences)
        if min_experience is not None and total_experience < min_experience:
            continue

        has_portfolio_flag = len(profile.portfolio_items) > 0

        candidates.append(
            HRCandidateShort(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                city=profile.city,
                desired_position=profile.desired_position,
                desired_salary=profile.desired_salary,
                has_portfolio=has_portfolio_flag,
                total_experience_years=total_experience,
            )
        )

    return candidates


async def add_candidate_note(
    session: AsyncSession,
    candidate_id: int,
    hr_id: int,
    data: dict,
) -> CandidateNote:
    note = CandidateNote(
        candidate_id=candidate_id,
        hr_id=hr_id,
        **data,
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


async def list_candidate_notes(
    session: AsyncSession,
    candidate_id: int,
) -> List[CandidateNote]:
    result = await session.execute(
        select(CandidateNote)
        .where(CandidateNote.candidate_id == candidate_id)
        .order_by(CandidateNote.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_candidate_note(
    session: AsyncSession,
    candidate_id: int,
    note_id: int,
    hr_id: int,
) -> None:
    result = await session.execute(
        select(CandidateNote).where(
            CandidateNote.id == note_id,
            CandidateNote.candidate_id == candidate_id,
            CandidateNote.hr_id == hr_id,
        )
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise ValueError("note_not_found")

    await session.delete(note)
    await session.commit()





async def update_application_hr_fields(
    session: AsyncSession,
    application_id: int,
    hr_id: int,
    data: dict,
) -> Application:
    # TODO: по-хорошему проверить, что этот HR имеет доступ к вакансии
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise ValueError("application_not_found")

    for field, value in data.items():
        setattr(application, field, value)

    await session.commit()
    await session.refresh(application)
    return application
