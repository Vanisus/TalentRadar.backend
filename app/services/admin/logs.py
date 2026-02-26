from pathlib import Path
from typing import Dict, Any, List

from app.config import settings


def read_last_log_lines(
    lines: int,
    log_filename: str = "app.log",
) -> Dict[str, Any]:
    """
    Прочитать последние N строк лог-файла.

    Возвращает:
      {
        "exists": bool,
        "total_lines": int | None,
        "returned_lines": int,
        "logs": List[str],
      }
    """
    log_file = Path(settings.LOG_DIR) / log_filename

    if not log_file.exists():
        return {
            "exists": False,
            "total_lines": None,
            "returned_lines": 0,
            "logs": [],
        }

    with log_file.open("r", encoding="utf-8") as f:
        all_lines: List[str] = f.readlines()

    last_lines = all_lines[-lines:] if lines > 0 else []

    return {
        "exists": True,
        "total_lines": len(all_lines),
        "returned_lines": len(last_lines),
        "logs": [line.strip() for line in last_lines],
    }
