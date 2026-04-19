from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    repo_root: Path = Path(os.getenv("REPO_ROOT", ".")).resolve()
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "kenya_hotels_pricing")
    run_label: str = os.getenv("INGESTION_RUN_LABEL", "manual")
    enable_ocr: bool = os.getenv("ENABLE_OCR", "false").lower() == "true"
    ocr_languages: str = os.getenv("OCR_LANGUAGES", "eng")
    max_text_chars: int = int(os.getenv("MAX_TEXT_CHARS", "30000"))


settings = Settings()
