from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ForbiddenError
from app.models.saved_search import SavedCandidateSearch
from app.models.user import User


async def create_saved_search_for_hr(
    session: AsyncSession,
    hr: User,
    name: str,
    params: Dict[str, Any],
) -> SavedCandidateSearch:
    saved = SavedCandidateSearch(
        hr_id=hr.id,
        name=name,
        params=params,
    )
    session.add(saved)
    await session.commit()
    await session.refresh(saved)
    return saved


async def list_saved_searches_for_hr(
    session: AsyncSession,
    hr: User,
) -> List[SavedCandidateSearch]:
    result = await session.execute(
        select(SavedCandidateSearch).where(SavedCandidateSearch.hr_id == hr.id)
    )
    return list(result.scalars().all())


async def get_saved_search_for_hr(
    session: AsyncSession,
    hr: User,
    search_id: int,
) -> SavedCandidateSearch:
    result = await session.execute(
        select(SavedCandidateSearch).where(SavedCandidateSearch.id == search_id)
    )
    saved = result.scalar_one_or_none()
    if saved is None:
        raise NotFoundError(
            message="Saved search not found",
            code="SAVED_SEARCH_NOT_FOUND",
            details={"search_id": search_id},
        )
    if saved.hr_id != hr.id:
        raise ForbiddenError(
            message="Forbidden",
            code="FORBIDDEN_SAVED_SEARCH_ACCESS",
            details={"search_id": search_id, "hr_id": hr.id},
        )
    return saved


async def delete_saved_search_for_hr(
    session: AsyncSession,
    hr: User,
    search_id: int,
) -> None:
    saved = await get_saved_search_for_hr(
        session=session,
        hr=hr,
        search_id=search_id,
    )
    await session.delete(saved)
    await session.commit()
