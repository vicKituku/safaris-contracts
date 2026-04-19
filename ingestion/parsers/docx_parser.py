from __future__ import annotations

from docx import Document

from ingestion.models import ParseResult, SourceFileRecord
from ingestion.parsers.base import BaseParser


class DocxParser(BaseParser):
    name = "docx_parser"

    def can_parse(self, source: SourceFileRecord) -> bool:
        return source.extension == ".docx"

    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        result = ParseResult(source_sha256=source.sha256, parser_name=self.name, parse_status="parsed")
        try:
            doc = Document(str(source.absolute_path))
            raw = "\n".join(p.text for p in doc.paragraphs if p.text)
            result.raw_text = raw[:max_chars]
            result.pages = None
            if not raw.strip():
                result.parse_status = "unparsed"
                result.warnings.append("DOCX had no text paragraphs.")
        except Exception as exc:
            result.parse_status = "failed"
            result.errors.append(str(exc))
        return result
