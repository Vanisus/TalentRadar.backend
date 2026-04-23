import json


RESUME_PARSE_SYSTEM_PROMPT = """
Ты — система структурированного парсинга резюме для HR-платформы TalentRadar.

Правила:
1. Извлекай только фактические данные, явно присутствующие в резюме.
2. Не выдумывай данные.
3. Если значение не найдено — используй null.
4. Если список отсутствует — используй [].
5. Возвращай только валидный JSON.
6. Не добавляй markdown, комментарии, пояснения или текст вне JSON.
7. Нормализуй даты в формат YYYY-MM, если месяц известен.
8. Если известен только год — используй YYYY.
9. Навыки разделяй на hard skills и soft skills.
10. В technologies включай только явно упомянутые технологии.
11. total_experience_months вычисляй только если это можно определить достаточно надёжно.
12. Если резюме содержит шум OCR, игнорируй мусор и извлекай только полезные HR-данные.
""".strip()


RESUME_JSON_SCHEMA = {
    "full_name": "string | null",
    "headline": "string | null",
    "location": "string | null",
    "contacts": {
        "email": "string | null",
        "phone": "string | null",
        "telegram": "string | null",
        "github": "string | null",
        "linkedin": "string | null",
        "website": "string | null",
    },
    "summary": "string | null",
    "desired_position": "string | null",
    "employment_type": "string | null",
    "work_format": "string | null",
    "total_experience_months": "integer | null",
    "skills_hard": ["string"],
    "skills_soft": ["string"],
    "languages": [
        {
            "name": "string",
            "level": "string | null",
        }
    ],
    "work_experience": [
        {
            "company": "string | null",
            "position": "string | null",
            "start_date": "YYYY-MM | YYYY | null",
            "end_date": "YYYY-MM | YYYY | null",
            "is_current": "boolean | null",
            "duration_months": "integer | null",
            "location": "string | null",
            "description": "string | null",
            "technologies": ["string"],
            "achievements": ["string"],
        }
    ],
    "education": [
        {
            "institution": "string | null",
            "degree": "string | null",
            "field_of_study": "string | null",
            "start_date": "YYYY-MM | YYYY | null",
            "end_date": "YYYY-MM | YYYY | null",
            "description": "string | null",
        }
    ],
    "certificates": [
        {
            "name": "string | null",
            "issuer": "string | null",
            "issue_date": "YYYY-MM | YYYY | null",
            "expiration_date": "YYYY-MM | YYYY | null",
            "credential_id": "string | null",
            "credential_url": "string | null",
        }
    ],
    "projects": [
        {
            "name": "string | null",
            "description": "string | null",
            "technologies": ["string"],
            "url": "string | null",
        }
    ],
    "portfolio_links": ["string"],
    "raw_sections": {
        "about": "string | null",
        "skills_block": "string | null",
        "experience_block": "string | null",
        "education_block": "string | null",
    },
}


def build_resume_parse_prompt(resume_text: str) -> str:
    return f"""
Извлеки структурированные данные из резюме по заданной JSON-схеме.

JSON-схема:
{json.dumps(RESUME_JSON_SCHEMA, ensure_ascii=False, indent=2)}

Текст резюме:
{resume_text}
""".strip()