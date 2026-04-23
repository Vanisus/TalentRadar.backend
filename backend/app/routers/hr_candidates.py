from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationHRUpdate, ApplicationRead
from app.schemas.hr_candidate import HRCandidateShort, HRCandidateProfile
from app.schemas.hr_note import CandidateNoteCreate, CandidateNoteRead
from app.services.hr.hr_candidates import (
    list_hr_candidates,
    get_hr_candidate_profile,
    add_candidate_note,
    list_candidate_notes,
    delete_candidate_note,
    update_application_hr_fields,
)
from app.schemas.hr_candidate_tag import CandidateTagCreate, CandidateTagRead
from app.services.hr.hr_candidate_tags import (
    add_candidate_tag_for_hr,
    list_candidate_tags_for_hr,
    delete_candidate_tag_for_hr,
)


router = APIRouter(
    prefix="/hr/candidates",
    tags=["HR Candidates"],
)


@router.get("", response_model=List[HRCandidateShort])
async def list_candidates_for_hr(
    limit: int = 20,
    offset: int = 0,
    city: Optional[str] = None,
    min_experience: Optional[float] = None,
    has_portfolio: Optional[bool] = None,
    skill: Optional[str] = None,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_hr_candidates(
        session=session,
        limit=limit,
        offset=offset,
        city=city,
        min_experience=min_experience,
        has_portfolio=has_portfolio,
        skill=skill,
    )


@router.get("/{candidate_id}/profile", response_model=HRCandidateProfile)
async def get_candidate_profile_for_hr(
    candidate_id: int,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    profile = await get_hr_candidate_profile(session=session, user_id=candidate_id)
    # get_hr_candidate_profile возвращает Optional, но отсутствие профиля — не ошибка домена,
    # поэтому тут можно оставить 404
    if profile is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or profile is empty",
        )
    return profile


@router.get(
    "/{candidate_id}/notes",
    response_model=List[CandidateNoteRead],
)
async def get_candidate_notes(
    candidate_id: int,
        session: AsyncSession = Depends(get_async_session),
):
    return await list_candidate_notes(session=session, candidate_id=candidate_id)


@router.post(
    "/{candidate_id}/notes",
    response_model=CandidateNoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_note(
    candidate_id: int,
    note_data: CandidateNoteCreate,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_candidate_note(
        session=session,
        candidate_id=candidate_id,
        hr_id=current_hr.id,
        data=note_data.model_dump(exclude_unset=True),
    )


@router.delete(
    "/{candidate_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_candidate_note_endpoint(
    candidate_id: int,
    note_id: int,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_candidate_note(
        session=session,
        candidate_id=candidate_id,
        note_id=note_id,
        hr_id=current_hr.id,
    )


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationRead,
)
async def update_application_for_hr(
    application_id: int,
    data: ApplicationHRUpdate,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    application = await update_application_hr_fields(
        session=session,
        application_id=application_id,
        hr_id=current_hr.id,
        data=data.model_dump(exclude_unset=True),
    )
    return application


@router.get("/applications/{application_id}", response_model=ApplicationRead)
async def get_application_for_hr(
    application_id: int,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return application


# ======== Теги HR по кандидату ========

@router.get(
    "/{candidate_id}/tags",
    response_model=list[CandidateTagRead],
)
async def get_candidate_tags(
    candidate_id: int,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_candidate_tags_for_hr(
        session=session,
        hr=current_hr,
        candidate_id=candidate_id,
    )


@router.post(
    "/{candidate_id}/tags",
    response_model=CandidateTagRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_tag(
    candidate_id: int,
    body: CandidateTagCreate,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_candidate_tag_for_hr(
        session=session,
        hr=current_hr,
        candidate_id=candidate_id,
        name=body.name,
    )


@router.delete(
    "/{candidate_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_candidate_tag(
    candidate_id: int,
    tag_id: int,
    current_hr: User = Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_candidate_tag_for_hr(
        session=session,
        hr=current_hr,
        candidate_id=candidate_id,
        tag_id=tag_id,
    )
