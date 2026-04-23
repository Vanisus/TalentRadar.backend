import json

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.parsed_resume import ParsedResume
from app.schemas.parsed_resume import ParsedResumePayload
from app.services.resume_prompt_service import (
    RESUME_PARSE_SYSTEM_PROMPT,
    build_resume_parse_prompt,
)


class ResumeParserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_get_parsed_resume(self, user) -> ParsedResume:
        result = await self.session.execute(
            select(ParsedResume).where(ParsedResume.user_id == user.id).order_by(ParsedResume.id.desc())
        )
        parsed_resume = result.scalars().first()

        if parsed_resume:
            return parsed_resume

        parsed_resume = ParsedResume(
            user_id=user.id,
            source_resume_path=getattr(user, "resume_path", None),
            source_resume_text=getattr(user, "resume_text", None),
            parse_status="pending",
            parser_version="resume_parser_v1",
        )
        self.session.add(parsed_resume)
        await self.session.flush()
        return parsed_resume

    async def parse_resume(self, user) -> ParsedResumePayload:
        parsed_resume = await self.create_or_get_parsed_resume(user)
        parsed_resume.parse_status = "processing"
        parsed_resume.error_message = None
        await self.session.commit()

        if not getattr(user, "resume_text", None):
            parsed_resume.parse_status = "failed"
            parsed_resume.error_message = "resume_text is empty"
            await self.session.commit()
            raise ValueError("resume_text is empty")

        payload = {
            "system_prompt": RESUME_PARSE_SYSTEM_PROMPT,
            "user_prompt": build_resume_parse_prompt(user.resume_text),
            "temperature": 0.1,
            "max_new_tokens": 2048,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.LLM_SERVICE_URL}/parse-resume",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            raw_json = data.get("parsed_json")
            if isinstance(raw_json, str):
                raw_json = json.loads(raw_json)

            validated = ParsedResumePayload.model_validate(raw_json)

            parsed_resume.source_resume_path = getattr(user, "resume_path", None)
            parsed_resume.source_resume_text = getattr(user, "resume_text", None)
            parsed_resume.parsed_json = validated.model_dump()
            parsed_resume.normalized_summary = validated.summary
            parsed_resume.parse_status = "completed"
            parsed_resume.error_message = None

            await self.session.commit()
            return validated

        except Exception as e:
            parsed_resume.parse_status = "failed"
            parsed_resume.error_message = str(e)
            await self.session.commit()
            raise

    async def map_to_domain_entities(self, user, parsed: ParsedResumePayload) -> None:
        if getattr(user, "full_name", None) != parsed.full_name and parsed.full_name:
            user.full_name = parsed.full_name

        profile = getattr(user, "candidate_profile", None)
        if profile:
            if hasattr(profile, "summary") and parsed.summary:
                profile.summary = parsed.summary
            if hasattr(profile, "location") and parsed.location:
                profile.location = parsed.location
            if hasattr(profile, "desired_position") and parsed.desired_position:
                profile.desired_position = parsed.desired_position

        # Ниже ты подставишь свои реальные модели и связи.
        # Логика правильная: очищаем старые AI-данные и пересобираем заново.
        #
        # examples:
        # await self.session.execute(delete(CandidateExperience).where(CandidateExperience.user_id == user.id))
        # for item in parsed.work_experience:
        #     self.session.add(CandidateExperience(...))
        #
        # await self.session.execute(delete(CandidateEducation).where(CandidateEducation.user_id == user.id))
        # for item in parsed.education:
        #     self.session.add(CandidateEducation(...))
        #
        # await self.session.execute(delete(CandidateCertificate).where(CandidateCertificate.user_id == user.id))
        # for item in parsed.certificates:
        #     self.session.add(CandidateCertificate(...))

        await self.session.commit()