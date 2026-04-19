from __future__ import annotations

from PIL import Image
import pytesseract

from ingestion.models import ParseResult, SourceFileRecord
from ingestion.parsers.base import BaseParser


class ImageParser(BaseParser):
    name = "image_parser"

    def __init__(self, enable_ocr: bool = False, ocr_languages: str = "eng") -> None:
        self.enable_ocr = enable_ocr
        self.ocr_languages = ocr_languages

    def can_parse(self, source: SourceFileRecord) -> bool:
        return source.extension in {".jpg", ".jpeg", ".png"}

    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        result = ParseResult(source_sha256=source.sha256, parser_name=self.name, parse_status="parsed")
        try:
            with Image.open(source.absolute_path) as img:
                meta = f"Image mode={img.mode} size={img.size} format={img.format}"
                result.raw_text = meta
                if self.enable_ocr:
                    extracted = pytesseract.image_to_string(img, lang=self.ocr_languages)
                    if extracted.strip():
                        result.raw_text = f"{meta}\n\nOCR:\n{extracted}"[:max_chars]
                    else:
                        result.warnings.append("OCR enabled but no text extracted.")
                else:
                    result.warnings.append("OCR disabled; image content left as metadata-only.")
        except Exception as exc:
            result.parse_status = "failed"
            result.errors.append(str(exc))
        return result
