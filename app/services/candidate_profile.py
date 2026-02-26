from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_profile import (
    CandidateProfile,
    WorkExperience,
    Education,
    CandidateSkill,
    Certificate,
    PortfolioItem,
)
from app.models.user import User


async def get_or_create_profile(
    session: AsyncSession,
    user: User,
    with_relations: bool = True,
) -> CandidateProfile:
    """
    Получить профиль кандидата, создать если не существует.
    Опционально подгружает связанные сущности.
    """
    query = select(CandidateProfile).where(CandidateProfile.user_id == user.id)

    if with_relations:
        query = query.options(
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.educations),
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.certificates),
            selectinload(CandidateProfile.portfolio_items),
        )

    result = await session.execute(query)
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        if with_relations:
            # заново загрузим с relations
            result = await session.execute(query)
            profile = result.scalar_one()

    return profile


async def update_profile(
    session: AsyncSession,
    user: User,
    update_data: dict,
) -> CandidateProfile:
    """
    Обновить профиль кандидата (создать, если нет) и вернуть с relations.
    """
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)

    for field, value in update_data.items():
        setattr(profile, field, value)

    await session.commit()
    await session.refresh(profile)

    # загрузим с relations
    result = await session.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.educations),
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.certificates),
            selectinload(CandidateProfile.portfolio_items),
        )
        .where(CandidateProfile.user_id == user.id)
    )
    return result.scalar_one()


async def add_experience(
    session: AsyncSession,
    user: User,
    data: dict,
) -> WorkExperience:
    profile = await get_or_create_profile(
        session=session,
        user=user,
        with_relations=False,
    )

    experience = WorkExperience(
        profile_id=profile.id,
        **data,
    )
    session.add(experience)
    await session.commit()
    await session.refresh(experience)
    return experience


async def list_experiences(
    session: AsyncSession,
    user: User,
) -> List[WorkExperience]:
    result = await session.execute(
        select(WorkExperience)
        .join(CandidateProfile, WorkExperience.profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(WorkExperience.start_date.desc())
    )
    return list(result.scalars().all())


async def update_experience(
    session: AsyncSession,
    user: User,
    experience_id: int,
    data: dict,
) -> WorkExperience:
    result = await session.execute(
        select(WorkExperience)
        .join(CandidateProfile, WorkExperience.profile_id == CandidateProfile.id)
        .where(
            WorkExperience.id == experience_id,
            CandidateProfile.user_id == user.id,
        )
    )
    experience = result.scalar_one_or_none()

    if experience is None:
        raise ValueError("experience_not_found")

    for field, value in data.items():
        setattr(experience, field, value)

    await session.commit()
    await session.refresh(experience)
    return experience


async def delete_experience(
    session: AsyncSession,
    user: User,
    experience_id: int,
) -> None:
    result = await session.execute(
        select(WorkExperience)
        .join(CandidateProfile, WorkExperience.profile_id == CandidateProfile.id)
        .where(
            WorkExperience.id == experience_id,
            CandidateProfile.user_id == user.id,
        )
    )
    experience = result.scalar_one_or_none()

    if experience is None:
        raise ValueError("experience_not_found")

    await session.delete(experience)
    await session.commit()

# ======== Education ========

async def add_education(
    session: AsyncSession,
    user: User,
    data: dict,
) -> Education:
    profile = await get_or_create_profile(
        session=session,
        user=user,
        with_relations=False,
    )
    edu = Education(profile_id=profile.id, **data)
    session.add(edu)
    await session.commit()
    await session.refresh(edu)
    return edu


async def list_educations(
    session: AsyncSession,
    user: User,
) -> List[Education]:
    result = await session.execute(
        select(Education)
        .join(CandidateProfile, Education.profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(Education.start_year.desc().nullslast())
    )
    return list(result.scalars().all())


async def update_education_service(
    session: AsyncSession,
    user: User,
    education_id: int,
    data: dict,
) -> Education:
    result = await session.execute(
        select(Education)
        .join(CandidateProfile, Education.profile_id == CandidateProfile.id)
        .where(
            Education.id == education_id,
            CandidateProfile.user_id == user.id,
        )
    )
    edu = result.scalar_one_or_none()
    if edu is None:
        raise ValueError("education_not_found")

    for field, value in data.items():
        setattr(edu, field, value)

    await session.commit()
    await session.refresh(edu)
    return edu


async def delete_education_service(
    session: AsyncSession,
    user: User,
    education_id: int,
) -> None:
    result = await session.execute(
        select(Education)
        .join(CandidateProfile, Education.profile_id == CandidateProfile.id)
        .where(
            Education.id == education_id,
            CandidateProfile.user_id == user.id,
        )
    )
    edu = result.scalar_one_or_none()
    if edu is None:
        raise ValueError("education_not_found")

    await session.delete(edu)
    await session.commit()


# ======== Skills ========

async def add_skill(
    session: AsyncSession,
    user: User,
    data: dict,
) -> CandidateSkill:
    profile = await get_or_create_profile(
        session=session,
        user=user,
        with_relations=False,
    )
    skill = CandidateSkill(profile_id=profile.id, **data)
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return skill


async def list_skills(
    session: AsyncSession,
    user: User,
) -> List[CandidateSkill]:
    result = await session.execute(
        select(CandidateSkill)
        .join(CandidateProfile, CandidateSkill.profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(CandidateSkill.name.asc())
    )
    return list(result.scalars().all())


async def delete_skill_service(
    session: AsyncSession,
    user: User,
    skill_id: int,
) -> None:
    result = await session.execute(
        select(CandidateSkill)
        .join(CandidateProfile, CandidateSkill.profile_id == CandidateProfile.id)
        .where(
            CandidateSkill.id == skill_id,
            CandidateProfile.user_id == user.id,
        )
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        raise ValueError("skill_not_found")

    await session.delete(skill)
    await session.commit()


# ======== Certificates ========

async def add_certificate(
    session: AsyncSession,
    user: User,
    data: dict,
) -> Certificate:
    profile = await get_or_create_profile(
        session=session,
        user=user,
        with_relations=False,
    )
    cert = Certificate(profile_id=profile.id, **data)
    session.add(cert)
    await session.commit()
    await session.refresh(cert)
    return cert


async def list_certificates(
    session: AsyncSession,
    user: User,
) -> List[Certificate]:
    result = await session.execute(
        select(Certificate)
        .join(CandidateProfile, Certificate.profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(Certificate.issue_date.desc().nullslast())
    )
    return list(result.scalars().all())


async def delete_certificate_service(
    session: AsyncSession,
    user: User,
    certificate_id: int,
) -> None:
    result = await session.execute(
        select(Certificate)
        .join(CandidateProfile, Certificate.profile_id == CandidateProfile.id)
        .where(
            Certificate.id == certificate_id,
            CandidateProfile.user_id == user.id,
        )
    )
    cert = result.scalar_one_or_none()
    if cert is None:
        raise ValueError("certificate_not_found")

    await session.delete(cert)
    await session.commit()


# ======== Portfolio ========

async def add_portfolio_item(
    session: AsyncSession,
    user: User,
    data: dict,
) -> PortfolioItem:
    profile = await get_or_create_profile(
        session=session,
        user=user,
        with_relations=False,
    )
    item = PortfolioItem(profile_id=profile.id, **data)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def list_portfolio_items(
    session: AsyncSession,
    user: User,
) -> List[PortfolioItem]:
    result = await session.execute(
        select(PortfolioItem)
        .join(CandidateProfile, PortfolioItem.profile_id == CandidateProfile.id)
        .where(CandidateProfile.user_id == user.id)
        .order_by(PortfolioItem.id.desc())
    )
    return list(result.scalars().all())


async def delete_portfolio_item_service(
    session: AsyncSession,
    user: User,
    item_id: int,
) -> None:
    result = await session.execute(
        select(PortfolioItem)
        .join(CandidateProfile, PortfolioItem.profile_id == CandidateProfile.id)
        .where(
            PortfolioItem.id == item_id,
            CandidateProfile.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise ValueError("portfolio_item_not_found")

    await session.delete(item)
    await session.commit()