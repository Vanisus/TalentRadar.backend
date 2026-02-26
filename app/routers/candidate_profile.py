from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_candidate
from app.models.user import User
from app.schemas.candidate_profile import (
    CandidateProfileRead,
    CandidateProfileUpdate,
    WorkExperienceCreate,
    WorkExperienceRead,
    EducationCreate,
    EducationRead,
    CandidateSkillCreate,
    CandidateSkillRead,
    CertificateCreate,
    CertificateRead,
    PortfolioItemCreate,
    PortfolioItemRead,
)
from app.services.candidate_profile import (
    get_or_create_profile,
    update_profile,
    add_experience,
    list_experiences,
    update_experience,
    delete_experience,
    add_education,
    list_educations,
    update_education_service,
    delete_education_service,
    add_skill,
    list_skills,
    delete_skill_service,
    add_certificate,
    list_certificates,
    delete_certificate_service,
    add_portfolio_item,
    list_portfolio_items,
    delete_portfolio_item_service,
)

router = APIRouter(
    prefix="/candidates/profile",
    tags=["Candidate Profile"],
)


# ======== Профиль целиком ========

@router.get("", response_model=CandidateProfileRead)
async def get_my_profile(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить свой структурированный профиль кандидата.
    Если профиля нет — создаётся пустой.
    """
    profile = await get_or_create_profile(
        session=session,
        user=current_user,
        with_relations=True,
    )
    return profile


@router.patch("", response_model=CandidateProfileRead)
async def update_my_profile(
    profile_data: CandidateProfileUpdate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Обновить свой структурированный профиль кандидата.
    Создаёт профиль, если его ещё нет.
    """
    update_data = profile_data.model_dump(exclude_unset=True)
    profile = await update_profile(
        session=session,
        user=current_user,
        update_data=update_data,
    )
    return profile


# ======== Опыт работы ========

@router.post(
    "/experiences",
    response_model=WorkExperienceRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_experience_endpoint(
    experience_data: WorkExperienceCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Добавить запись об опыте работы в профиль.
    """
    experience = await add_experience(
        session=session,
        user=current_user,
        data=experience_data.model_dump(exclude_unset=True),
    )
    return experience


@router.get(
    "/experiences",
    response_model=List[WorkExperienceRead],
)
async def get_my_experiences_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить все записи опыта работы из своего профиля.
    """
    experiences = await list_experiences(session=session, user=current_user)
    return experiences


@router.patch(
    "/experiences/{experience_id}",
    response_model=WorkExperienceRead,
)
async def update_experience_endpoint(
    experience_id: int,
    experience_data: WorkExperienceCreate,  # позже можно заменить на WorkExperienceUpdate
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Обновить запись опыта работы.
    """
    try:
        experience = await update_experience(
            session=session,
            user=current_user,
            experience_id=experience_id,
            data=experience_data.model_dump(exclude_unset=True),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found",
        )

    return experience


@router.delete(
    "/experiences/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_experience_endpoint(
    experience_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Удалить запись опыта работы из своего профиля.
    """
    try:
        await delete_experience(
            session=session,
            user=current_user,
            experience_id=experience_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found",
        )


# ======== Образование ========

@router.post(
    "/educations",
    response_model=EducationRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_education_endpoint(
    education_data: EducationCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    edu = await add_education(
        session=session,
        user=current_user,
        data=education_data.model_dump(exclude_unset=True),
    )
    return edu


@router.get(
    "/educations",
    response_model=List[EducationRead],
)
async def get_my_educations_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    educations = await list_educations(session=session, user=current_user)
    return educations


@router.patch(
    "/educations/{education_id}",
    response_model=EducationRead,
)
async def update_education_endpoint(
    education_id: int,
    education_data: EducationCreate,  # позже можно сделать EducationUpdate
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        edu = await update_education_service(
            session=session,
            user=current_user,
            education_id=education_id,
            data=education_data.model_dump(exclude_unset=True),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found",
        )
    return edu


@router.delete(
    "/educations/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_education_endpoint(
    education_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await delete_education_service(
            session=session,
            user=current_user,
            education_id=education_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found",
        )



# ======== Навыки ========

@router.post(
    "/skills",
    response_model=CandidateSkillRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_skill_endpoint(
    skill_data: CandidateSkillCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    skill = await add_skill(
        session=session,
        user=current_user,
        data=skill_data.model_dump(exclude_unset=True),
    )
    return skill


@router.get(
    "/skills",
    response_model=List[CandidateSkillRead],
)
async def get_my_skills_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    skills = await list_skills(session=session, user=current_user)
    return skills


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_skill_endpoint(
    skill_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await delete_skill_service(
            session=session,
            user=current_user,
            skill_id=skill_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )



# ======== Сертификаты ========

@router.post(
    "/certificates",
    response_model=CertificateRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_certificate_endpoint(
    certificate_data: CertificateCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    cert = await add_certificate(
        session=session,
        user=current_user,
        data=certificate_data.model_dump(exclude_unset=True),
    )
    return cert


@router.get(
    "/certificates",
    response_model=List[CertificateRead],
)
async def get_my_certificates_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    certs = await list_certificates(session=session, user=current_user)
    return certs


@router.delete(
    "/certificates/{certificate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_certificate_endpoint(
    certificate_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await delete_certificate_service(
            session=session,
            user=current_user,
            certificate_id=certificate_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )



# ======== Портфолио ========

@router.post(
    "/portfolio",
    response_model=PortfolioItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_portfolio_item_endpoint(
    item_data: PortfolioItemCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    item = await add_portfolio_item(
        session=session,
        user=current_user,
        data=item_data.model_dump(exclude_unset=True),
    )
    return item


@router.get(
    "/portfolio",
    response_model=List[PortfolioItemRead],
)
async def get_my_portfolio_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    items = await list_portfolio_items(session=session, user=current_user)
    return items


@router.delete(
    "/portfolio/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_portfolio_item_endpoint(
    item_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        await delete_portfolio_item_service(
            session=session,
            user=current_user,
            item_id=item_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found",
        )

