from __future__ import annotations

from pypdf import PdfReader

from ingestion.models import ParseResult, SourceFileRecord
from ingestion.parsers.base import BaseParser


class PdfParser(BaseParser):
    name = "pdf_parser"

    def can_parse(self, source: SourceFileRecord) -> bool:
        return source.extension == ".pdf"

    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        result = ParseResult(source_sha256=source.sha256, parser_name=self.name, parse_status="parsed")
        try:
            reader = PdfReader(str(source.absolute_path))
            texts: list[str] = []
            for page in reader.pages:
                texts.append(page.extract_text() or "")
            raw = "\n".join(texts)
            result.raw_text = raw[:max_chars]
            result.pages = len(reader.pages)
            if not raw.strip():
                result.parse_status = "unparsed"
                result.warnings.append("PDF had no extractable text; likely scanned/image-based.")
        except Exception as exc:
            result.parse_status = "failed"
            result.errors.append(str(exc))
        return result
