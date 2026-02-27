import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

# ---- Константы ----

SECTION_HEADERS = {
    "experience": [
        "опыт работы",
        "опыт",
        "professional experience",
        "experience",
        "work experience",
        "employment history",
    ],
    "education": [
        "образование",
        "education",
    ],
    "skills": [
        "ключевые навыки",
        "навыки",
        "skills",
        "technical skills",
    ],
    "about": [
        "о себе",
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
    Грубое разбиение резюме на секции по заголовкам.
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

    # чисто цифры: '03.2020' или '2020'
    if "." in s or s.isdigit():
        try:
            if "." in s:
                m_str, y_str = s.split(".", 1)
                m = int(m_str)
                y = int(y_str)
                if 1 <= m <= 12:
                    return m, y
                return 1, y
            # только год
            y = int(s)
            return 1, y
        except ValueError:
            return None, None

    # 'январь 2020', 'января 2020', 'january 2020', 'jan 2020'
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
    Очень грубый парсер опыта:
    - опыт разделён пустыми строками
    - первая строка блока: должность + компания (эвристика)
    - даты: 'ММ.ГГГГ', 'ГГГГ', 'январь 2020', 'January 2020', '... — по настоящее время'
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    experiences: List[Dict[str, Any]] = []

    date_pattern = re.compile(
        r"(?P<start>(\d{2}\.\d{4}|\d{4}|[А-Яа-яA-Za-z]+ \d{4}))"
        r"\s*[-–—]?\s*"
        r"(?P<end>(\d{2}\.\d{4}|\d{4}|[А-Яа-яA-Za-z]+ \d{4}|по настоящее время|настоящее время|по н\.в\.)|)?",
        re.IGNORECASE,
    )

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        title_company = lines[0]
        position = title_company
        company: Optional[str] = None

        for sep in ("—", "-", "–", ","):
            if sep in title_company:
                left, right = title_company.split(sep, 1)
                position = left.strip()
                company = right.strip()
                break

        dates_match = date_pattern.search(block)
        start_date: Optional[date] = None
        end_date: Optional[date] = None
        is_current = False

        if dates_match:
            start_raw = dates_match.group("start")
            end_raw = dates_match.group("end")

            sm, sy = _parse_month_year_str(start_raw)
            if sy is not None:
                start_date = date(sy, sm or 1, 1)

            if end_raw:
                end_raw_norm = end_raw.lower()
                if "настоя" in end_raw_norm or "н.в" in end_raw_norm:
                    is_current = True
                    end_date = None
                else:
                    em, ey = _parse_month_year_str(end_raw)
                    if ey is not None:
                        end_date = date(ey, em or 1, 1)

        description = "\n".join(lines[1:]).strip() or None

        # если не смогли вытащить год начала — пропускаем блок,
        # чтобы не ломать NOT NULL по start_date
        if start_date is None:
            continue

        experiences.append(
            {
                "company": company or "",
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
    Простейший парсер образования:
    - ищем годы
    - собираем остальной текст как institution/field_of_study
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    educations: List[Dict[str, Any]] = []

    year_pattern = re.compile(r"(19\d{2}|20\d{2})")

    current: Dict[str, Any] = {}
    for line in lines:
        year_nums = year_pattern.findall(line)

        if year_nums:
            if current:
                educations.append(current)
                current = {}

            current["start_year"] = int(year_nums[0])
            if len(year_nums) > 1:
                current["end_year"] = int(year_nums[1])

            current.setdefault("institution", line)
        else:
            if "institution" not in current:
                current["institution"] = line
            else:
                field = current.get("field_of_study")
                current["field_of_study"] = (
                    f"{field} {line}".strip() if field else line
                )

    if current:
        educations.append(current)

    for edu in educations:
        edu.setdefault("degree", None)
        edu.setdefault("field_of_study", None)

    return educations


def _parse_skills_section(text: str) -> List[Dict[str, Any]]:
    """
    Навыки: через запятую или по строкам.
    Фильтруем слишком длинные куски, чтобы не тащить целые абзацы.
    """
    skills: List[Dict[str, Any]] = []

    normalized = re.sub(r"\s+", " ", text).strip()

    if "," in normalized:
        raw_parts = normalized.split(",")
    else:
        raw_parts = [l.strip() for l in text.split("\n")]

    MAX_SKILL_LEN = 100
    MAX_ACCEPTABLE_LEN = 80

    for raw in raw_parts:
        p = raw.strip()
        if not p:
            continue

        if len(p) > MAX_ACCEPTABLE_LEN:
            continue

        p = p.rstrip(";. ")

        if not p:
            continue

        if len(p) > MAX_SKILL_LEN:
            p = p[:MAX_SKILL_LEN]

        skills.append({"name": p, "level": None})

    return skills


def _parse_about_section(text: str) -> Dict[str, Any]:
    return {"about_me": text.strip()}


def _parse_certificates_section(text: str) -> List[Dict[str, Any]]:
    """
    Каждая строка = сертификат.
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


def build_profile_from_resume_text(resume_text: str) -> Dict[str, Any]:
    """
    Построить структурированный профиль из текста резюме.
    Формат:
      {
        "profile": {...},
        "experiences": [...],
        "educations": [...],
        "skills": [...],
        "certificates": [...],
      }
    """
    sections = _split_sections(resume_text)

    profile: Dict[str, Any] = {}
    experiences: List[Dict[str, Any]] = []
    educations: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []
    certificates: List[Dict[str, Any]] = []

    for section in sections:
        if section.name == "about":
            profile.update(_parse_about_section(section.text))
        elif section.name == "experience":
            experiences.extend(_parse_experience_section(section.text))
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
