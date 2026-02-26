import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


SECTION_HEADERS = {
    "experience": [
        "опыт работы",
        "опыт",
        "professional experience",
        "experience",
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


@dataclass
class Section:
    name: str
    text: str


def _normalize_text(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text).strip()


def _split_sections(resume_text: str) -> List[Section]:
    """
    Грубое разбиение резюме на секции по заголовкам.
    """
    text = _normalize_text(resume_text)

    header_patterns: List[str] = []
    for key, headers in SECTION_HEADERS.items():
        for h in headers:
            header_patterns.append(
                rf"(?P<{key}>^\s*{re.escape(h)}\s*:?\s*$)"
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


def _parse_experience_section(text: str) -> List[Dict[str, Any]]:
    """
    Очень грубый парсер опыта:
    - опыт разделён пустыми строками
    - первая строка блока: должность + компания (эвристика)
    - даты формата 'ММ.ГГГГ' или 'ГГГГ'
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    experiences: List[Dict[str, Any]] = []

    date_pattern = re.compile(
        r"(?P<start>(\d{2}\.\d{4}|\d{4}))\s*[-–—]?\s*(?P<end>(\d{2}\.\d{4}|\d{4}|по настоящее время|настоящее время|по н\.в\.)|)?",
        re.IGNORECASE,
    )

    def _parse_date(s: str | None) -> Optional[date]:
        if not s:
            return None
        try:
            if "." in s:
                m, y = s.split(".")
                return date(int(y), int(m), 1)
            return date(int(s), 1, 1)
        except ValueError:
            return None

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

            start_date = _parse_date(start_raw)

            if end_raw:
                end_raw_norm = end_raw.lower()
                if "настоя" in end_raw_norm:
                    is_current = True
                    end_date = None
                else:
                    end_date = _parse_date(end_raw)

        description = "\n".join(lines[1:]).strip() or None

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
                current["field_of_study"] = f"{field} {line}".strip() if field else line

    if current:
        educations.append(current)

    for edu in educations:
        edu.setdefault("degree", None)
        edu.setdefault("field_of_study", None)

    return educations


def _parse_skills_section(text: str) -> List[Dict[str, Any]]:
    """
    Навыки: через запятую или по строкам.
    """
    skills: List[Dict[str, Any]] = []

    if "," in text:
        parts = [p.strip() for p in text.replace("\n", " ").split(",") if p.strip()]
    else:
        parts = [l.strip() for l in text.split("\n") if l.strip()]

    for p in parts:
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
