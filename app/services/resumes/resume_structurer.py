import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

# ---- Константы ----

SECTION_HEADERS = {
    "experience": [
    "опыт работы",
    "опыт работы —",
    "experience",
    "work experience",
    "employment history",
    ],
    "education": [
        "образование",
        "education",
    ],
    "skills": [
        "навыки",
        "skills",
        "technical skills",
    ],
    "about": [
        "дополнительная информация",
        "о себе",
        "обо мне",
        "summary",
        "about me",
        "profile",
    ],
    "certificates": [
        "сертификаты",
        "курсы",
        "courses",
        "certifications",
    ],
}

MONTHS_MAP = {
    # русские
    "январь": 1, "января": 1,
    "февраль": 2, "февраля": 2,
    "март": 3, "марта": 3,
    "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июнь": 6, "июня": 6,
    "июль": 7, "июля": 7,
    "август": 8, "августа": 8,
    "сентябрь": 9, "сентября": 9,
    "октябрь": 10, "октября": 10,
    "ноябрь": 11, "ноября": 11,
    "декабрь": 12, "декабря": 12,
    # английские
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


@dataclass
class Section:
    name: str
    text: str


# ---- Вспомогательные функции ----

def _normalize_text(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text).strip()


def _split_sections(resume_text: str) -> List[Section]:
    """
    Разбиваем резюме на крупные секции по заголовкам.
    Для твоего резюме важны: Опыт работы, Образование, Навыки, Доп. информация.
    """
    text = _normalize_text(resume_text)

    header_patterns: List[str] = []
    for key, headers in SECTION_HEADERS.items():
        escaped_headers = [re.escape(h) for h in headers]
        alternatives = "|".join(escaped_headers)
        header_patterns.append(
            rf"(?P<{key}>^\s*(?:{alternatives})\s*:?\s*$)"
        )

    if not header_patterns:
        return [Section(name="root", text=text)]

    regex = re.compile("|".join(header_patterns), re.IGNORECASE | re.MULTILINE)

    sections: List[Section] = []
    current_name = "root"
    current_start = 0

    for match in regex.finditer(text):
        section_text = text[current_start:match.start()].strip()
        if section_text:
            sections.append(Section(name=current_name, text=section_text))

        for key in SECTION_HEADERS.keys():
            if match.groupdict().get(key):
                current_name = key
                break

        current_start = match.end()

    tail = text[current_start:].strip()
    if tail:
        sections.append(Section(name=current_name, text=tail))

    return sections


def _parse_month_year_str(s: str | None) -> tuple[Optional[int], Optional[int]]:
    """
    Парсер строки даты в (month, year).
    Поддерживаем:
      - '03.2020'
      - '2020'
      - 'январь 2020', 'января 2020'
      - 'January 2020', 'Jan 2020'
    """
    if not s:
        return None, None

    s = s.strip().lower()
    s = s.replace("г.", "").replace("год", "").replace("года", "").strip()

    # '03.2020' или '2020'
    if "." in s or s.isdigit():
        try:
            if "." in s:
                m_str, y_str = s.split(".", 1)
                m = int(m_str)
                y = int(y_str)
                if 1 <= m <= 12:
                    return m, y
                return 1, y
            y = int(s)
            return 1, y
        except ValueError:
            return None, None

    # 'январь 2020', 'January 2020', ...
    parts = s.split()
    if len(parts) >= 2:
        month_name = parts[0]
        year_part = parts[1]
        m = MONTHS_MAP.get(month_name)
        try:
            y = int(year_part)
        except ValueError:
            return None, None
        if m is None:
            m = 1
        return m, y

    return None, None


# ---- Парсеры секций ----

def _parse_experience_section(text: str) -> List[Dict[str, Any]]:
    """
    Парсер опыта под hh-формат:
    - ищем первую строку 'Опыт работы' и парсим только после неё;
    - блок:
        <Месяц ГГГГ [— ...]>
        [настоящее время]
        [строка типа '1 год 5 месяцев']
        <company>
        <position>
        <описание...>
    """
    all_lines = [l.strip() for l in text.split("\n")]

    # 0) ограничимся только текстом ПОСЛЕ 'Опыт работы'
    start_experience_idx = None
    for idx, line in enumerate(all_lines):
        if line.lower().startswith("опыт работы"):
            start_experience_idx = idx + 1
            break

    if start_experience_idx is None:
        return []

    lines = [l for l in all_lines[start_experience_idx:] if l.strip()]
    experiences: List[Dict[str, Any]] = []
    n = len(lines)

    # Строка, которая выглядит как 'Октябрь 2024', 'Июнь 2023' и т.п.
    month_name_pattern = r"[А-Яа-яA-Za-z]+"
    date_line_pattern = re.compile(
        rf"^(?P<start>{month_name_pattern}\s+\d{{4}})(\s*[—-]\s*(?P<end>{month_name_pattern}\s+\d{{4}}))?$",
        re.IGNORECASE,
    )

    i = 0
    while i < n:
        m = date_line_pattern.match(lines[i])
        if not m:
            i += 1
            continue

        start_raw = m.group("start")
        end_raw = m.group("end")

        # возможно, на следующей строке стоит 'настоящее время'
        is_current = False
        if i + 1 < n and "настоящее время" in lines[i + 1].lower():
            is_current = True
            end_raw = lines[i + 1]
            i += 1

        # пропускаем строку стажа '1 год 5 месяцев' и т.п.
        if i + 1 < n and re.search(
            r"\d+\s+год|\d+\s+года|\d+\s+лет|\d+\s+месяц|\d+\s+месяцев",
            lines[i + 1],
            re.IGNORECASE,
        ):
            i += 1

        # company
        i += 1
        if i >= n:
            break
        company = lines[i]

        # position
        i += 1
        if i >= n:
            break
        position = lines[i]

        # описание
        i += 1
        description_lines: List[str] = []
        while i < n and not date_line_pattern.match(lines[i]):
            # останавливаемся, если встретили заголовок другой секции
            if any(
                lines[i].lower().startswith(h.lower())
                for h_list in SECTION_HEADERS.values()
                for h in h_list
            ):
                break
            description_lines.append(lines[i])
            i += 1

        # парсим даты
        sm, sy = _parse_month_year_str(start_raw)
        start_date: Optional[date] = None
        end_date: Optional[date] = None

        if sy is not None:
            start_date = date(sy, sm or 1, 1)

        if end_raw:
            end_norm = end_raw.lower()
            if "настоя" in end_norm or "н.в" in end_norm:
                is_current = True
                end_date = None
            else:
                em, ey = _parse_month_year_str(end_raw)
                if ey is not None:
                    end_date = date(ey, em or 1, 1)

        if start_date is None:
            continue

        description = "\n".join(description_lines).strip() or None

        experiences.append(
            {
                "company": company,
                "position": position,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "is_current": is_current,
            }
        )

    return experiences


def _parse_education_section(text: str) -> List[Dict[str, Any]]:
    """
    Парсер образования под твой кейс hh.ru:
    Образование
    Бакалавр
    2024
    Бакалавр
    [строки вуза...]
    Программная инженерия, Разработчик

    + фильтрация служебных строк 'Резюме обновлено ...'.
    """
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]

    # выкидываем служебные строки hh
    lines = [
        l for l in raw_lines
        if not l.lower().startswith("резюме обновлено")
    ]

    educations: List[Dict[str, Any]] = []
    if not lines:
        return educations

    year_re = re.compile(r"^(19\d{2}|20\d{2})$")

    degree: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    institution_lines: List[str] = []
    field_of_study: Optional[str] = None

    i = 0
    n = len(lines)

    # первая строка после 'Образование' — степень
    if i < n and not year_re.match(lines[i]):
        degree = lines[i]
        i += 1

    # следующая строка может быть либо чистым годом,
    # либо '2024 Саратовский ...'
    if i < n:
        parts = lines[i].split(" ", 1)
        if year_re.match(parts[0]):
            year_val = int(parts[0])
            start_year = year_val
            end_year = year_val
            # если дальше есть текст — он часть вуза
            if len(parts) > 1 and parts[1].strip():
                institution_lines.append(parts[1].strip())
            i += 1

    # иногда степень дублируется после года
    if i < n and not year_re.match(lines[i]):
        if degree is None:
            degree = lines[i]
        else:
            # скорее всего это уже вуз
            institution_lines.append(lines[i])
        i += 1

    # остальное: строки вуза + последняя строка как field_of_study
    remaining = lines[i:]
    if remaining:
        if len(remaining) > 1:
            institution_lines.extend(remaining[:-1])
            field_of_study = remaining[-1]
        else:
            institution_lines.extend(remaining)

    institution = " ".join(institution_lines).strip() if institution_lines else None

    if institution:
        educations.append(
            {
                "institution": institution,
                "degree": degree,
                "field_of_study": field_of_study,
                "start_year": start_year,
                "end_year": end_year,
            }
        )

    return educations



def _parse_skills_section(text: str) -> List[Dict[str, Any]]:
    """
    Навыки под формат hh.ru:
    - игнорируем блок 'Знание языков' и строки с уровнями языков;
    - забираем всё, что идёт после слова 'Навыки' до 'Опыт вождения';
    - режем по 2+ пробелам, оставляя фразы (REST API, Базы данных и т.п.);
    - убираем дубли.
    """
    skills: List[Dict[str, Any]] = []

    lines = [l.rstrip() for l in text.split("\n")]

    # 1) Сужаемся до блока между вторым 'Навыки' и 'Опыт вождения'
    start_idx = None
    seen_nav = 0
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith("навыки"):
            seen_nav += 1
            if seen_nav == 2:
                start_idx = idx
                break

    if start_idx is None:
        relevant_lines = lines
    else:
        relevant_lines = lines[start_idx :]

    cut_lines: List[str] = []
    for line in relevant_lines:
        if line.strip().lower().startswith("опыт вождения"):
            break
        # выкидываем строку 'Знание языков' и строки с языками (Английский — B1 — Средний и т.п.)
        low = line.strip().lower()
        if low.startswith("знание языков"):
            continue
        if "— b1" in low or "— c1" in low or "— a2" in low:
            # грубая эвристика для строк с уровнями языков
            continue
        cut_lines.append(line)

    # 2) Разбираем строки:
    # - если строка начинается с 'Навыки', берём только часть после этого слова;
    # - остальные строки используем целиком.
    raw_parts: List[str] = []
    for line in cut_lines:
        stripped = line.strip()
        if not stripped:
            continue

        low = stripped.lower()
        if low.startswith("навыки"):
            # берём всё после слова 'Навыки'
            after = stripped[len("Навыки") :].strip()
            if not after:
                continue
            # режем по 2+ пробелам, чтобы получить группы
            parts = [p.strip() for p in re.split(r"\s{2,}", after) if p.strip()]
            raw_parts.extend(parts)
        else:
            # для остальных строк: режем по 2+ пробелам, оставляя фразы
            parts = [p.strip() for p in re.split(r"\s{2,}", stripped) if p.strip()]
            raw_parts.extend(parts)

    MAX_SKILL_LEN = 100
    MAX_ACCEPTABLE_LEN = 80

    seen: set[str] = set()
    ordered_skills: List[str] = []

    for p in raw_parts:
        if not p:
            continue
        if len(p) > MAX_ACCEPTABLE_LEN:
            continue

        p = p.rstrip(";.,")

        if not p:
            continue

        if len(p) > MAX_SKILL_LEN:
            p = p[:MAX_SKILL_LEN]

        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered_skills.append(p)

    return [{"name": name, "level": None} for name in ordered_skills]


def _parse_about_section(text: str) -> Dict[str, Any]:
    """
    'Дополнительная информация' / 'Обо мне' → один большой текст в about_me.
    """
    return {"about_me": text.strip()}


def _parse_certificates_section(text: str) -> List[Dict[str, Any]]:
    """
    Каждая строка = сертификат.
    Сейчас в твоём резюме явного блока сертификатов нет, но оставим задел.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return [
        {
            "title": line,
            "issuer": None,
            "issue_date": None,
            "file_path": None,
        }
        for line in lines
    ]


# ---- Входная точка ----

def build_profile_from_resume_text(resume_text: str) -> Dict[str, Any]:
    """
    Построить структурированный профиль из текста резюме.
    """
    sections = _split_sections(resume_text)

    profile: Dict[str, Any] = {}
    educations: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []
    certificates: List[Dict[str, Any]] = []

    # 1) Опыт всегда парсим из ВСЕГО текста, чтобы не зависеть от заголовка
    experiences = _parse_experience_section(resume_text)

    # 2) Остальное — по секциям
    for section in sections:
        if section.name == "about":
            profile.update(_parse_about_section(section.text))
        elif section.name == "education":
            educations.extend(_parse_education_section(section.text))
        elif section.name == "skills":
            skills.extend(_parse_skills_section(section.text))
        elif section.name == "certificates":
            certificates.extend(_parse_certificates_section(section.text))
        else:
            continue

    return {
        "profile": profile,
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "certificates": certificates,
    }

