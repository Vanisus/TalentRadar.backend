def calculate_match_score(resume_text: str, required_skills: list[str]) -> float:
    """
    Простой расчёт соответствия резюме требованиям вакансии
    Возвращает процент совпадения (0-100)
    """
    if not resume_text or not required_skills:
        return 0.0

    # Приводим к нижнему регистру для сравнения
    resume_lower = resume_text.lower()

    matched_skills = 0
    for skill in required_skills:
        if skill.lower() in resume_lower:
            matched_skills += 1

    # Процент совпадения
    match_percentage = (matched_skills / len(required_skills)) * 100

    return round(match_percentage, 2)
