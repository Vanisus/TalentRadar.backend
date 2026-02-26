from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_hr
from app.schemas.application import ApplicationHRUpdate, ApplicationRead
from app.schemas.hr_candidate import HRCandidateShort, HRCandidateProfile
from app.schemas.hr_note import CandidateNoteCreate, CandidateNoteRead
from app.services.hr_candidates import (
    list_hr_candidates,
    get_hr_candidate_profile,
    add_candidate_note,
    list_candidate_notes,
    delete_candidate_note,
)
from app.models.application import Application
from sqlalchemy import select
from app.services.hr_candidates import update_application_hr_fields

router = APIRouter(
    prefix="/hr/candidates",
    tags=["HR Candidates"],
)


@router.get("", response_model=List[HRCandidateShort])
async def list_candidates_for_hr(
    limit: int = 20,
    offset: int = 0,
    city: str | None = None,
    min_experience: float | None = None,
    has_portfolio: bool | None = None,
    skill: str | None = None,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Список кандидатов для HR с краткой карточкой и фильтрами:
    - city
    - min_experience (лет)
    - has_portfolio
    - skill (поиск по названию навыка)
    """
    candidates = await list_hr_candidates(
        session=session,
        limit=limit,
        offset=offset,
        city=city,
        min_experience=min_experience,
        has_portfolio=has_portfolio,
        skill=skill,
    )
    return candidates



@router.get("/{candidate_id}/profile", response_model=HRCandidateProfile)
async def get_candidate_profile_for_hr(
    candidate_id: int,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Полный профиль кандидата для HR:
    - базовая инфа (ФИО, контакты, город)
    - желаемая позиция и зарплата
    - опыт, образование, навыки, сертификаты, портфолио
    """
    profile = await get_hr_candidate_profile(session=session, user_id=candidate_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or profile is empty",
        )
    return profile

# ======== Заметки HR по кандидату ========

@router.get(
    "/{candidate_id}/notes",
    response_model=list[CandidateNoteRead],
)
async def get_candidate_notes(
    candidate_id: int,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить все заметки по кандидату (видны всем HR).
    """
    notes = await list_candidate_notes(session=session, candidate_id=candidate_id)
    return notes


@router.post(
    "/{candidate_id}/notes",
    response_model=CandidateNoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_note(
    candidate_id: int,
    note_data: CandidateNoteCreate,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Добавить заметку по кандидату от текущего HR.
    """
    note = await add_candidate_note(
        session=session,
        candidate_id=candidate_id,
        hr_id=current_hr.id,
        data=note_data.model_dump(exclude_unset=True),
    )
    return note


@router.delete(
    "/{candidate_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_candidate_note_endpoint(
    candidate_id: int,
    note_id: int,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Удалить свою заметку по кандидату.
    HR может удалять только свои заметки.
    """
    try:
        await delete_candidate_note(
            session=session,
            candidate_id=candidate_id,
            note_id=note_id,
            hr_id=current_hr.id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationRead,
)
async def update_application_for_hr(
    application_id: int,
    data: ApplicationHRUpdate,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Обновить поля заявки, которые относятся к HR:
    - rating
    - pipeline_stage
    """
    try:
        application = await update_application_hr_fields(
            session=session,
            application_id=application_id,
            hr_id=current_hr.id,
            data=data.model_dump(exclude_unset=True),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application



@router.get("/applications/{application_id}", response_model=ApplicationRead)
async def get_application_for_hr(
    application_id: int,
    current_hr=Depends(get_current_hr),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить заявку с полями, полезными для HR:
    - статус, rating, pipeline_stage, match_summary.
    """
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return application
