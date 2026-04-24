# app/services/candidate/resume_parser_service.py
import json
import logging
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parsed_resume import ParsedResume
from app.models.candidate_profile import (
    CandidateProfile,
    WorkExperience,
    Education,
    CandidateSkill,
    Certificate,
)
from app.services.llm.client import call_llm_parse_resume

logger = logging.getLogger(__name__)


class ResumeParserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def parse_and_save(
        self,
        user_id: int,
        resume_text: str,
        resume_path: str | None = None,
    ) -> ParsedResume:
        """
        Вызывает llm-service для парсинга резюме.
        Сохраняет ParsedResume в БД.
        Обновляет профиль кандидата реальными данными.
        """
        # 1) Создаём запись со статусом pending
        parsed = ParsedResume(
            user_id=user_id,
            source_resume_path=resume_path,
            source_resume_text=resume_text,
            parse_status="pending",
            parser_version="llm_v1",
        )
        self.session.add(parsed)
        await self.session.flush()  # получаем id без коммита

        try:
            # 2) Вызываем llm-service
            llm_response = await call_llm_parse_resume(resume_text)
            parsed_json = llm_response.get("parsed_json", {})

            # 3) Сохраняем результат
            parsed.parsed_json = parsed_json
            parsed.normalized_summary = json.dumps(parsed_json, ensure_ascii=False)
            parsed.parse_status = "success"

            # 4) Обновляем CandidateProfile
            await self._update_profile_from_json(user_id, parsed_json)

        except Exception as e:
            logger.error(f"LLM parse failed for user {user_id}: {e}")
            parsed.parse_status = "failed"
            parsed.error_message = str(e)
            # Не бросаем — чтобы не сломать загрузку резюме

        return parsed

    async def _update_profile_from_json(self, user_id: int, data: dict) -> None:
        result = await self.session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return

        # Перезаписываем базовые поля
        for json_key, model_field in {
            "full_name": "full_name",
            "desired_position": "desired_position",
            "city": "city",
            "phone": "phone",
            "email": "email",
            "about_me": "about_me",
        }.items():
            value = data.get(json_key)
            if value:
                setattr(profile, model_field, value)

        # Чистим старые связанные записи и пишем новые
        await self.session.execute(
            sa.delete(CandidateSkill).where(CandidateSkill.profile_id == profile.id)
        )
        await self.session.execute(
            sa.delete(WorkExperience).where(WorkExperience.profile_id == profile.id)
        )
        await self.session.execute(
            sa.delete(Education).where(Education.profile_id == profile.id)
        )
        await self.session.execute(
            sa.delete(Certificate).where(Certificate.profile_id == profile.id)
        )

        for skill_name in data.get("skills", []):
            self.session.add(CandidateSkill(profile_id=profile.id, name=skill_name))

        for exp in data.get("experiences", []):
            self.session.add(WorkExperience(
                profile_id=profile.id,
                company=exp.get("company", ""),
                position=exp.get("position", ""),
                description=exp.get("description"),
                start_date=_parse_date(exp.get("start_date")),
                end_date=_parse_date(exp.get("end_date")),
                is_current=exp.get("is_current", False),
            ))

        for edu in data.get("educations", []):
            self.session.add(Education(
                profile_id=profile.id,
                institution=edu.get("institution", ""),
                degree=edu.get("degree"),
                field_of_study=edu.get("field_of_study"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
            ))

        for cert in data.get("certificates", []):
            self.session.add(Certificate(
                profile_id=profile.id,
                title=cert.get("title", ""),
                issuer=cert.get("issuer"),
                issue_date=_parse_date(cert.get("issue_date")),
            ))




def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None