from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ingestion.models import SourceFileRecord

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".zip": "application/zip",
    ".mp4": "video/mp4",
}


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()


def infer_destination_hotel(relative_path: Path) -> tuple[str | None, str | None]:
    parts = relative_path.parts
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    if len(parts) == 1:
        return parts[0].strip(), None
    return None, None


def scan_repository(repo_root: Path) -> Iterable[SourceFileRecord]:
    for path in repo_root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(repo_root)
        destination_name, hotel_name = infer_destination_hotel(rel)
        stat = path.stat()
        ext = path.suffix.lower()
        yield SourceFileRecord(
            relative_path=str(rel),
            absolute_path=path,
            extension=ext,
            mime_hint=MIME_BY_EXT.get(ext, "application/octet-stream"),
            file_size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            sha256=sha256_file(path),
            destination_name=destination_name,
            hotel_name=hotel_name,
        )
