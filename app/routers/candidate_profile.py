from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, File, Form
from app.schemas.certificate_upload import CertificateUploadResponse
from app.services.candidate.certificate_upload import handle_certificate_upload

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
from app.schemas.resume_summary import ResumeSummary
from app.services.candidate.resume_center import get_resume_summary_for_candidate
from app.services.candidate.candidate_profile import (
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
from app.services.resumes.resume_status import get_resume_status_for_candidate

router = APIRouter(
    prefix="/candidates/profile",
    tags=["Candidate Profile"],
)


@router.get("", response_model=CandidateProfileRead)
async def get_my_profile(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
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
    update_data = profile_data.model_dump(exclude_unset=True)
    profile = await update_profile(
        session=session,
        user=current_user,
        update_data=update_data,
    )
    return profile

@router.get("/resume/status")
async def get_resume_status(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_resume_status_for_candidate(
        session=session,
        user=current_user,
    )
# ======== Experience ========

@router.post(
    "/experiences",
    response_model=WorkExperienceRead,
    status_code=201,
)
async def add_experience_endpoint(
    experience_data: WorkExperienceCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_experience(
        session=session,
        user=current_user,
        data=experience_data.model_dump(exclude_unset=True),
    )


@router.get(
    "/experiences",
    response_model=List[WorkExperienceRead],
)
async def get_my_experiences_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_experiences(session=session, user=current_user)


@router.patch(
    "/experiences/{experience_id}",
    response_model=WorkExperienceRead,
)
async def update_experience_endpoint(
    experience_id: int,
    experience_data: WorkExperienceCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_experience(
        session=session,
        user=current_user,
        experience_id=experience_id,
        data=experience_data.model_dump(exclude_unset=True),
    )


@router.delete(
    "/experiences/{experience_id}",
    status_code=204,
)
async def delete_experience_endpoint(
    experience_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_experience(
        session=session,
        user=current_user,
        experience_id=experience_id,
    )


# ======== Education ========

@router.post(
    "/educations",
    response_model=EducationRead,
    status_code=201,
)
async def add_education_endpoint(
    education_data: EducationCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_education(
        session=session,
        user=current_user,
        data=education_data.model_dump(exclude_unset=True),
    )


@router.get(
    "/educations",
    response_model=List[EducationRead],
)
async def get_my_educations_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_educations(session=session, user=current_user)


@router.patch(
    "/educations/{education_id}",
    response_model=EducationRead,
)
async def update_education_endpoint(
    education_id: int,
    education_data: EducationCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await update_education_service(
        session=session,
        user=current_user,
        education_id=education_id,
        data=education_data.model_dump(exclude_unset=True),
    )


@router.delete(
    "/educations/{education_id}",
    status_code=204,
)
async def delete_education_endpoint(
    education_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_education_service(
        session=session,
        user=current_user,
        education_id=education_id,
    )


# ======== Skills ========

@router.post(
    "/skills",
    response_model=CandidateSkillRead,
    status_code=201,
)
async def add_skill_endpoint(
    skill_data: CandidateSkillCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_skill(
        session=session,
        user=current_user,
        data=skill_data.model_dump(exclude_unset=True),
    )


@router.get(
    "/skills",
    response_model=List[CandidateSkillRead],
)
async def get_my_skills_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_skills(session=session, user=current_user)


@router.delete(
    "/skills/{skill_id}",
    status_code=204,
)
async def delete_skill_endpoint(
    skill_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_skill_service(
        session=session,
        user=current_user,
        skill_id=skill_id,
    )


# ======== Certificates ========

@router.post(
    "/certificates",
    response_model=CertificateRead,
    status_code=201,
)
async def add_certificate_endpoint(
    certificate_data: CertificateCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_certificate(
        session=session,
        user=current_user,
        data=certificate_data.model_dump(exclude_unset=True),
    )


@router.get(
    "/certificates",
    response_model=List[CertificateRead],
)
async def get_my_certificates_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_certificates(session=session, user=current_user)


@router.delete(
    "/certificates/{certificate_id}",
    status_code=204,
)
async def delete_certificate_endpoint(
    certificate_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_certificate_service(
        session=session,
        user=current_user,
        certificate_id=certificate_id,
    )


# ======== Portfolio ========

@router.post(
    "/portfolio",
    response_model=PortfolioItemRead,
    status_code=201,
)
async def add_portfolio_item_endpoint(
    item_data: PortfolioItemCreate,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await add_portfolio_item(
        session=session,
        user=current_user,
        data=item_data.model_dump(exclude_unset=True),
    )


@router.get(
    "/portfolio",
    response_model=List[PortfolioItemRead],
)
async def get_my_portfolio_endpoint(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_portfolio_items(session=session, user=current_user)


@router.delete(
    "/portfolio/{item_id}",
    status_code=204,
)
async def delete_portfolio_item_endpoint(
    item_id: int,
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_portfolio_item_service(
        session=session,
        user=current_user,
        item_id=item_id,
    )


@router.get("/resume/summary", response_model=ResumeSummary)
async def get_resume_summary(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Центр резюме кандидата:
    - статус резюме
    - длина текста
    - процент заполнения профиля
    - краткие рекомендации по навыкам (если есть резюме и вакансии)
    """
    return await get_resume_summary_for_candidate(
        session=session,
        candidate=current_user,
    )


@router.get(
    "/portfolio_items",
    response_model=List[PortfolioItemRead],
)
async def get_my_portfolio_items(
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получить все элементы портфолио из своего профиля.
    """
    items = await list_portfolio_items(session=session, user=current_user)
    return items


@router.post("/certificates/upload", response_model=CertificateRead)
async def upload_certificate(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    current_user: User = Depends(get_current_candidate),
    session: AsyncSession = Depends(get_async_session),
):
    cert = await handle_certificate_upload(
        session=session,
        user=current_user,
        file=file,
        title=title,
    )
    return cert
