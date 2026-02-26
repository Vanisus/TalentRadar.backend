from collections import Counter
from typing import List, Dict, Any


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
