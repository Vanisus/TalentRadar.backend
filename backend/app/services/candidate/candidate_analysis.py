from typing import List, Dict, Any


def analyze_candidate_match(
        resume_text: str,
        required_skills: List[str]
) -> Dict[str, Any]:
    """
    Детальный анализ соответствия кандидата требованиям вакансии.
    Всегда возвращает все поля, совместимые с CandidateMatchAnalysis.
    """
    total = len(required_skills) if required_skills else 0

    if not resume_text or not required_skills:
        return {
            "passes": False,
            "match_score": 0.0,
            "matched_skills": [],
            "missing_skills": required_skills if required_skills else [],
            "matched_skills_count": 0,
            "missing_skills_count": total,
            "total_required_skills": total,
            "explanation": (
                "Резюме отсутствует или требования вакансии не указаны"
                if not resume_text
                else "Требования вакансии не указаны"
            ),
        }

    resume_lower = resume_text.lower()
    matched_skills: List[str] = []
    missing_skills: List[str] = []

    for skill in required_skills:
        if skill.lower() in resume_lower:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    match_score = round((len(matched_skills) / total) * 100, 2) if total else 0.0
    passes = match_score >= 50.0

    if passes:
        if match_score >= 70:
            explanation = (
                f"Кандидат хорошо подходит на вакансию. Совпадение: {match_score}%. "
                f"Найдено {len(matched_skills)} из {total} требуемых навыков."
            )
            if missing_skills:
                explanation += f" Отсутствуют навыки: {', '.join(missing_skills)}."
        else:
            explanation = (
                f"Кандидат подходит на вакансию. Совпадение: {match_score}%. "
                f"Найдено {len(matched_skills)} из {total} требуемых навыков."
            )
            if missing_skills:
                explanation += (
                    f" Рекомендуется обратить внимание на отсутствующие навыки: "
                    f"{', '.join(missing_skills)}."
                )
    else:
        explanation = (
            f"Кандидат не подходит на вакансию. Совпадение: {match_score}%. "
            f"Найдено только {len(matched_skills)} из {total} требуемых навыков."
        )
        if missing_skills:
            explanation += f" Отсутствуют следующие навыки: {', '.join(missing_skills)}."

    return {
        "passes": passes,
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_skills_count": len(matched_skills),
        "missing_skills_count": len(missing_skills),
        "total_required_skills": total,
        "explanation": explanation,
    }
