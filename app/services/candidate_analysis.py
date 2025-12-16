from typing import List, Dict, Any


def analyze_candidate_match(
    resume_text: str,
    required_skills: List[str]
) -> Dict[str, Any]:
    """
    Детальный анализ соответствия кандидата требованиям вакансии
    
    Args:
        resume_text: Текст резюме кандидата
        required_skills: Список требуемых навыков для вакансии
        
    Returns:
        Словарь с детальным анализом соответствия
    """
    if not resume_text or not required_skills:
        return {
            "passes": False,
            "match_score": 0.0,
            "matched_skills": [],
            "missing_skills": required_skills if required_skills else [],
            "missing_skills_count": len(required_skills) if required_skills else 0,
            "explanation": "Резюме отсутствует или требования вакансии не указаны" if not resume_text else "Требования вакансии не указаны"
        }
    
    resume_lower = resume_text.lower()
    
    # Анализируем каждый требуемый навык
    matched_skills = []
    missing_skills = []
    
    for skill in required_skills:
        skill_lower = skill.lower()
        if skill_lower in resume_lower:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)
    
    # Рассчитываем процент совпадения
    match_score = (len(matched_skills) / len(required_skills)) * 100 if required_skills else 0.0
    match_score = round(match_score, 2)
    
    # Определяем, проходит ли кандидат
    # Кандидат проходит, если совпадение >= 50%
    passes = match_score >= 50.0
    
    # Формируем объяснение
    explanation = ""
    if passes:
        if match_score >= 70:
            explanation = f"Кандидат хорошо подходит на вакансию. Совпадение: {match_score}%. Найдено {len(matched_skills)} из {len(required_skills)} требуемых навыков."
            if missing_skills:
                explanation += f" Отсутствуют навыки: {', '.join(missing_skills)}."
        elif match_score >= 50:
            explanation = f"Кандидат подходит на вакансию. Совпадение: {match_score}%. Найдено {len(matched_skills)} из {len(required_skills)} требуемых навыков."
            if missing_skills:
                explanation += f" Рекомендуется обратить внимание на отсутствующие навыки: {', '.join(missing_skills)}."
    else:
        explanation = f"Кандидат не подходит на вакансию. Совпадение: {match_score}%. Найдено только {len(matched_skills)} из {len(required_skills)} требуемых навыков."
        if missing_skills:
            explanation += f" Отсутствуют следующие навыки: {', '.join(missing_skills)}."
    
    return {
        "passes": passes,
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_skills_count": len(matched_skills),
        "missing_skills_count": len(missing_skills),
        "total_required_skills": len(required_skills),
        "explanation": explanation
    }

