from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ForbiddenError
from app.models.user import User
from app.models.candidate_tag import CandidateTag  # твоя модель тегов


async def add_candidate_tag_for_hr(
    session: AsyncSession,
    hr: User,
    candidate_id: int,
    name: str,
) -> CandidateTag:
    tag = CandidateTag(
        candidate_id=candidate_id,
        hr_id=hr.id,
        name=name,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def list_candidate_tags_for_hr(
    session: AsyncSession,
    hr: User,
    candidate_id: int,
) -> List[CandidateTag]:
    result = await session.execute(
        select(CandidateTag).where(
            CandidateTag.candidate_id == candidate_id,
            CandidateTag.hr_id == hr.id,
        )
    )
    return list(result.scalars().all())


async def delete_candidate_tag_for_hr(
    session: AsyncSession,
    hr: User,
    candidate_id: int,
    tag_id: int,
) -> None:
    result = await session.execute(
        select(CandidateTag).where(
            CandidateTag.id == tag_id,
            CandidateTag.candidate_id == candidate_id,
        )
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise NotFoundError(
            message="Candidate tag not found",
            code="CANDIDATE_TAG_NOT_FOUND",
            details={"tag_id": tag_id, "candidate_id": candidate_id},
        )
    if tag.hr_id != hr.id:
        raise ForbiddenError(
            message="Forbidden",
            code="FORBIDDEN_CANDIDATE_TAG_ACCESS",
            details={"tag_id": tag_id, "hr_id": hr.id},
        )

    await session.delete(tag)
    await session.commit()
