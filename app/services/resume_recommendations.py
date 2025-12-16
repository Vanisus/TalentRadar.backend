from collections import Counter
from typing import List, Dict


def analyze_resume_improvements(
    resume_text: str,
    all_vacancy_skills: List[List[str]]
) -> Dict:
    """
    Анализирует резюме и генерирует рекомендации по улучшению
    
    Args:
        resume_text: Текст резюме кандидата
        all_vacancy_skills: Список списков навыков из всех вакансий
        
    Returns:
        Словарь с рекомендациями
    """
    if not resume_text or not all_vacancy_skills:
        return {
            "missing_skills": [],
            "popular_skills": [],
            "resume_stats": {},
            "general_recommendations": []
        }
    
    resume_lower = resume_text.lower()
    
    # Собираем все навыки из всех вакансий
    all_skills = []
    for skills_list in all_vacancy_skills:
        all_skills.extend(skills_list)
    
    # Подсчитываем частоту навыков
    skills_counter = Counter([skill.lower() for skill in all_skills])
    
    # Определяем популярные навыки (встречаются в 2+ вакансиях)
    popular_skills = [
        skill for skill, count in skills_counter.items()
        if count >= 2
    ]
    popular_skills.sort(key=lambda x: skills_counter[x], reverse=True)
    
    # Находим навыки, которых нет в резюме
    missing_skills = []
    for skill in popular_skills:
        # Проверяем наличие навыка в резюме (без учета регистра)
        if skill not in resume_lower:
            # Находим оригинальное название навыка (с правильным регистром)
            original_skill = next(
                (s for s in all_skills if s.lower() == skill),
                skill.capitalize()
            )
            missing_skills.append({
                "skill": original_skill,
                "frequency": skills_counter[skill],
                "percentage_of_vacancies": round((skills_counter[skill] / len(all_vacancy_skills)) * 100, 1) if all_vacancy_skills else 0
            })
    
    # Сортируем по частоте использования
    missing_skills.sort(key=lambda x: x["frequency"], reverse=True)
    
    # Анализ статистики резюме
    resume_length = len(resume_text)
    word_count = len(resume_text.split())
    
    # Проверяем наличие ключевых секций
    has_contact = any(keyword in resume_lower for keyword in ["email", "телефон", "phone", "@", "контакт"])
    has_experience = any(keyword in resume_lower for keyword in ["опыт", "experience", "работал", "работала", "работа"])
    has_education = any(keyword in resume_lower for keyword in ["образование", "education", "университет", "институт", "вуз"])
    has_skills = any(keyword in resume_lower for keyword in ["навыки", "skills", "умения", "компетенции"])
    
    resume_stats = {
        "length": resume_length,
        "word_count": word_count,
        "has_contact_info": has_contact,
        "has_experience": has_experience,
        "has_education": has_education,
        "has_skills_section": has_skills
    }
    
    # Генерируем общие рекомендации
    general_recommendations = []
    
    if resume_length < 500:
        general_recommendations.append({
            "type": "length",
            "priority": "high",
            "message": "Резюме слишком короткое. Рекомендуется добавить больше информации об опыте работы, проектах и навыках.",
            "details": f"Текущая длина: {resume_length} символов. Рекомендуется: не менее 500-800 символов."
        })
    elif resume_length > 5000:
        general_recommendations.append({
            "type": "length",
            "priority": "medium",
            "message": "Резюме слишком длинное. Рекомендуется сократить до наиболее важной информации.",
            "details": f"Текущая длина: {resume_length} символов. Рекомендуется: не более 3000-4000 символов."
        })
    
    if not has_contact:
        general_recommendations.append({
            "type": "contact",
            "priority": "high",
            "message": "Добавьте контактную информацию (email, телефон) в резюме.",
            "details": "Контактная информация необходима для связи с потенциальными работодателями."
        })
    
    if not has_experience:
        general_recommendations.append({
            "type": "experience",
            "priority": "medium",
            "message": "Добавьте раздел об опыте работы.",
            "details": "Работодатели оценивают опыт работы как один из ключевых факторов при отборе кандидатов."
        })
    
    if not has_education:
        general_recommendations.append({
            "type": "education",
            "priority": "low",
            "message": "Добавьте информацию об образовании.",
            "details": "Образование может быть важным фактором для некоторых позиций."
        })
    
    if not has_skills:
        general_recommendations.append({
            "type": "skills_section",
            "priority": "medium",
            "message": "Добавьте отдельный раздел с навыками и компетенциями.",
            "details": "Выделенный раздел с навыками помогает работодателям быстро оценить вашу квалификацию."
        })
    
    # Рекомендации по популярным навыкам
    if missing_skills:
        top_missing = missing_skills[:10]  # Топ-10 отсутствующих навыков
        general_recommendations.append({
            "type": "missing_skills",
            "priority": "high",
            "message": f"Рассмотрите возможность добавить популярные навыки: {', '.join([s['skill'] for s in top_missing[:5]])}",
            "details": f"Эти навыки встречаются в {top_missing[0]['percentage_of_vacancies']}% вакансий и могут увеличить ваши шансы на трудоустройство."
        })
    
    return {
        "missing_skills": missing_skills[:15],  # Топ-15 отсутствующих навыков
        "popular_skills": [{"skill": skill, "frequency": skills_counter[skill]} for skill in popular_skills[:20]],  # Топ-20 популярных навыков
        "resume_stats": resume_stats,
        "general_recommendations": general_recommendations
    }

