from __future__ import annotations

from config import Settings
from ingestion.models import ParseResult, SourceFileRecord
from ingestion.parsers.base import BaseParser
from ingestion.parsers.docx_parser import DocxParser
from ingestion.parsers.fallback_parser import FallbackParser
from ingestion.parsers.image_parser import ImageParser
from ingestion.parsers.pdf_parser import PdfParser


class ParserRegistry:
    def __init__(self, settings: Settings) -> None:
        self.parsers: list[BaseParser] = [
            PdfParser(),
            DocxParser(),
            ImageParser(enable_ocr=settings.enable_ocr, ocr_languages=settings.ocr_languages),
            FallbackParser(),
        ]

    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        parser = next(p for p in self.parsers if p.can_parse(source))
        return parser.parse(source, max_chars)
