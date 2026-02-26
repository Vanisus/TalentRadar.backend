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
    # Убираем лишние пробелы, приводим к unix-строкам
    return re.sub(r"\r\n?", "\n", text).strip()


def _split_sections(resume_text: str) -> List[Section]:
    """
    Грубое разбиение резюме на секции по заголовкам.
    """
    text = _normalize_text(resume_text)

    # Подготовим паттерн для всех заголовков
    header_patterns = []
    for key, headers in SECTION_HEADERS.items():
        for h in headers:
            # ^\s*(опыт работы)\s*:?
            header_patterns.append(
                rf"(?P<{key}>^\s*{re.escape(h)}\s*:?\s*$)"
            )

    combined_pattern = "|".join(header_patterns)
    regex = re.compile(combined_pattern, re.IGNORECASE | re.MULTILINE)

    sections: List[Section] = []
    current_name = "root"
    current_start = 0

    for match in regex.finditer(text):
        # Сохраняем предыдущий блок
        if current_name is not None:
            section_text = text[current_start:match.start()].strip()
            if section_text:
                sections.append(Section(name=current_name, text=section_text))

        # Определяем новое имя секции по именованному груп-матчу
        for key in SECTION_HEADERS.keys():
            if match.group(key):
                current_name = key
                break

        current_start = match.end()

    # Хвост
    tail = text[current_start:].strip()
    if tail:
        sections.append(Section(name=current_name, text=tail))

    return sections


def _parse_experience_section(text: str) -> List[Dict[str, Any]]:
    """
    Очень грубый парсер опыта:
    - предполагаем, что опыт разделён пустыми строками
    - первая строка блока: должность + компания (эвристика)
    - ищем даты формата 'ММ.ГГГГ' или 'ГГГГ' и 'по настоящее время'
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    experiences: List[Dict[str, Any]] = []

    date_pattern = re.compile(
        r"(?P<start>(\d{2}\.\d{4}|\d{4}))\s*(?:[-–—]\s*(?P<end>(\d{2}\.\d{4}|\d{4}|по настоящее время|настоящее время|по н\.в\.)))?",
        re.IGNORECASE,
    )

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        # Первая строка: должность + компания (эвристика — разделяем по "—" или "," первые два куска)
        title_company = lines[0]
        position = title_company
        company = None

        # Попробуем разбить по "—" или "-"
        for sep in ("—", "-", "–", ","):
            if sep in title_company:
                parts = [p.strip() for p in title_company.split(sep, 1)]
                if len(parts) == 2:
                    position, company = parts[0], parts[1]
                    break

        # Ищем даты в блоке
        dates_match = date_pattern.search(block)
        start_date: Optional[date] = None
        end_date: Optional[date] = None
        is_current = False

        if dates_match:
            start_raw = dates_match.group("start")
            end_raw = dates_match.group("end")

            def parse_year_or_month_year(s: str) -> Optional[date]:
                if not s:
                    return None
                try:
                    if "." in s:
                        m, y = s.split(".")
                        return date(int(y), int(m), 1)
                    return date(int(s), 1, 1)
                except ValueError:
                    return None

            start_date = parse_year_or_month_year(start_raw)

            if end_raw:
                end_raw_norm = end_raw.lower()
                if "настоя" in end_raw_norm:
                    is_current = True
                    end_date = None
                else:
                    end_date = parse_year_or_month_year(end_raw)

        description_lines = lines[1:]
        description = "\n".join(description_lines).strip() or None

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
    Примерно делим по строкам, ищем год и ВУЗ.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    educations: List[Dict[str, Any]] = []

    year_pattern = re.compile(r"(19|20)\d{2}")

    current: Dict[str, Any] = {}
    for line in lines:
        years = year_pattern.findall(line)
        if years:
            # новая запись образования
            if current:
                educations.append(current)
                current = {}

            # возьмём первый и, возможно, второй год
            nums = re.findall(r"(19|20)\d{2}", line)
            # nums в виде [ ('20','20'), ... ] — для простоты вытащим через другой regex
            year_nums = re.findall(r"(19\d{2}|20\d{2})", line)
            if year_nums:
                current["start_year"] = int(year_nums[0])
                if len(year_nums) > 1:
                    current["end_year"] = int(year_nums[1])

            # ВУЗ и специальность просто сохраним в institution
            current.setdefault("institution", line)
        else:
            # Остальные строки добавляем в institution/field_of_study
            if "institution" not in current:
                current["institution"] = line
            else:
                # если есть поле field_of_study — дописываем туда
                existing = current.get("field_of_study")
                if existing:
                    current["field_of_study"] = existing + " " + line
                else:
                    current["field_of_study"] = line

    if current:
        educations.append(current)

    # Проставим дефолты
    for edu in educations:
        edu.setdefault("degree", None)
        edu.setdefault("field_of_study", None)

    return educations


def _parse_skills_section(text: str) -> List[Dict[str, Any]]:
    """
    Навыки обычно перечислены через запятую или построчно.
    """
    skills: List[Dict[str, Any]] = []

    # Сначала попробуем разделить по запятой — для hh это частый случай
    if "," in text:
        parts = [p.strip() for p in text.replace("\n", " ").split(",") if p.strip()]
        for p in parts:
            skills.append({"name": p, "level": None})
    else:
        # Иначе — каждая непустая строка = навык
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for l in lines:
            skills.append({"name": l, "level": None})

    return skills


def _parse_about_section(text: str) -> Dict[str, Any]:
    """
    Просто возвращаем текст 'О себе'.
    """
    return {"about_me": text.strip()}


def _parse_certificates_section(text: str) -> List[Dict[str, Any]]:
    """
    Простейший парсер сертификатов: каждая строка = отдельный сертификат.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    certificates: List[Dict[str, Any]] = []

    for line in lines:
        certificates.append(
            {
                "title": line,
                "issuer": None,
                "issue_date": None,
                "file_path": None,
            }
        )

    return certificates


def build_profile_from_resume_text(resume_text: str) -> Dict[str, Any]:
    """
    Построить структурированный профиль из текста резюме.
    Возвращает dict вида:
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
            # root или неизвестная секция — можно в будущем использовать для доп. эвристик
            continue

    return {
        "profile": profile,
        "experiences": experiences,
        "educations": educations,
        "skills": skills,
        "certificates": certificates,
    }
