from collections import Counter
from typing import Any, Dict, List

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profile import (
    CandidateProfile,
    WorkExperience,
    Education,
    CandidateSkill,
)
from app.models.user import User


def analyze_resume_improvements(
        resume_text: str,
        all_vacancy_skills: List[List[str]],
) -> Dict[str, Any]:
    """
    Лёгкий анализ резюме:
    - какие популярные навыки из вакансий отсутствуют в резюме
    - базовая статистика по тексту
    """
    if not resume_text or not all_vacancy_skills:
        return {
            "missing_skills": [],
            "popular_skills": [],
            "resume_stats": {
                "length": len(resume_text or ""),
                "word_count": len((resume_text or "").split()),
            },
        }

    resume_lower = resume_text.lower()

    # Собираем и считаем все навыки из вакансий
    all_skills: List[str] = []
    for skills_list in all_vacancy_skills:
        all_skills.extend(skills_list)

    skills_counter = Counter(skill.lower() for skill in all_skills)

    # Популярные навыки (встречаются хотя бы в 2 вакансиях)
    popular_skills_sorted = sorted(
        skills_counter.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )

    # Навыки, которых нет в резюме
    missing_skills: List[Dict[str, Any]] = []
    total_vacancies = len(all_vacancy_skills)

    for skill_lower, freq in popular_skills_sorted:
        if freq < 2:
            continue

        if skill_lower in resume_lower:
            continue

        original_skill = next(
            (s for s in all_skills if s.lower() == skill_lower),
            skill_lower.capitalize(),
        )

        missing_skills.append(
            {
                "skill": original_skill,
                "frequency": freq,
                "percentage_of_vacancies": round(
                    freq / total_vacancies * 100.0, 1
                )
                if total_vacancies
                else 0.0,
            }
        )

    # Топ-15 отсутствующих и топ-20 популярных навыков
    missing_skills = missing_skills[:15]
    popular_skills = [
        {"skill": next((s for s in all_skills if s.lower() == skill_lower), skill_lower.capitalize()),
         "frequency": freq}
        for skill_lower, freq in popular_skills_sorted[:20]
    ]

    resume_stats = {
        "length": len(resume_text),
        "word_count": len(resume_text.split()),
    }

    return {
        "missing_skills": missing_skills,
        "popular_skills": popular_skills,
        "resume_stats": resume_stats,
    }


async def get_resume_recommendations_for_candidate(
        session: AsyncSession,
        current_user: User,
) -> Dict[str, Any]:
    # профиль
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return {
            "recommendations": [
                "Создайте профиль кандидата.",
                "Загрузите резюме в формате PDF или DOCX.",
            ]
        }

    # считаем сущности
    exp_count = await session.scalar(
        select(sa.func.count(WorkExperience.id)).where(
            WorkExperience.profile_id == profile.id
        )
    )
    edu_count = await session.scalar(
        select(sa.func.count(Education.id)).where(
            Education.profile_id == profile.id
        )
    )
    skills_count = await session.scalar(
        select(sa.func.count(CandidateSkill.id)).where(
            CandidateSkill.profile_id == profile.id
        )
    )

    recs: List[str] = []

    # файл резюме
    has_resume_file = bool(
        getattr(profile, "resume_file_path", None)
        or getattr(current_user, "resume_path", None)
    )
    if not has_resume_file:
        recs.append("Загрузите файл резюме, чтобы мы могли лучше проанализировать ваш опыт.")

    if not profile.desired_position:
        recs.append("Укажите желаемую должность в профиле.")

    if exp_count == 0:
        recs.append("Добавьте хотя бы одно место работы в раздел «Опыт работы».")
    elif exp_count < 2:
        recs.append("Расширьте раздел «Опыт работы», опишите 2–3 ключевых места работы.")

    if edu_count == 0:
        recs.append("Заполните раздел «Образование» (вуз, год окончания, направление).")

    if skills_count == 0:
        recs.append("Добавьте ключевые навыки, соответствующие вашей специализации.")

    if not profile.about_me:
        recs.append("Заполните блок «Обо мне», кратко опишите свой опыт и сильные стороны.")

    if not recs:
        recs.append("Ваше резюме выглядит заполненным. При желании уточните навыки и опыт.")

    return {"recommendations": recs}
