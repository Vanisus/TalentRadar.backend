import shutil
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import BadRequestError
from app.models.candidate_profile import CandidateProfile, Certificate
from app.models.user import User

ALLOWED_CERT_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]


def _ensure_dirs() -> tuple[Path, Path]:
    base_dir = Path(settings.UPLOAD_DIR) / "certificates"
    preview_dir = base_dir / "previews"
    base_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    return base_dir, preview_dir


def _build_safe_filename(user_id: int, filename: str) -> str:
    safe_name = filename.replace(" ", "_")
    return f"user_{user_id}_{safe_name}"


def _generate_pdf_preview(src_path: Path, preview_path: Path) -> None:
    """
    Генерация превью первой страницы PDF в PNG.
    Требуется pdf2image + poppler в системе.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        # Если нет pdf2image, можно просто пропустить превью
        return

    try:
        pages = convert_from_path(str(src_path), first_page=1, last_page=1)
        if not pages:
            return
        page = pages[0]
        page.save(preview_path, "PNG")
    except Exception:
        # Не роняем процесс из-за проблем с превью
        return


async def handle_certificate_upload(
    session: AsyncSession,
    user: User,
    file: UploadFile,
    title: Optional[str] = None,
) -> Certificate:
    base_dir, preview_dir = _ensure_dirs()

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_CERT_EXTENSIONS:
        raise BadRequestError(
            message="Invalid certificate file format",
            code="INVALID_CERTIFICATE_FORMAT",
            details={
                "allowed_extensions": ALLOWED_CERT_EXTENSIONS,
                "got_extension": ext,
            },
        )

    safe_name = _build_safe_filename(user.id, file.filename)
    file_path = base_dir / safe_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Профиль
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    # Превью
    preview_rel_path: Optional[str] = None
    if ext == ".pdf":
        preview_filename = f"{file_path.stem}_preview.png"
        preview_full_path = preview_dir / preview_filename
        _generate_pdf_preview(file_path, preview_full_path)
        if preview_full_path.exists():
            # храним относительные пути от UPLOAD_DIR
            preview_rel_path = str(
                Path("certificates") / "previews" / preview_filename
            )
    elif ext in {".png", ".jpg", ".jpeg"}:
        # для изображений можно использовать сам файл как превью
        preview_rel_path = str(Path("certificates") / safe_name)

    cert = Certificate(
        profile_id=profile.id,
        title=title or Path(file.filename).stem,
        issuer=None,
        issue_date=None,
        file_path=str(Path("certificates") / safe_name),
        preview_path=preview_rel_path,
    )
    session.add(cert)
    await session.commit()
    await session.refresh(cert)
    return cert
