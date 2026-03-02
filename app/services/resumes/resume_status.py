from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import CandidateProfile
from app.models.user import User


async def get_resume_status_for_candidate(
    session: AsyncSession,
    user: User,
) -> Dict[str, Any]:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile: Optional[CandidateProfile] = result.scalar_one_or_none()

    has_file = bool(profile and profile.resume_file_path)

    return {
        "has_resume_file": has_file,
        "resume_file_path": profile.resume_file_path if has_file else None,
    }
