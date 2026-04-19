from __future__ import annotations

from ingestion.models import ParseResult, SourceFileRecord
from ingestion.parsers.base import BaseParser


class FallbackParser(BaseParser):
    name = "fallback_parser"

    def can_parse(self, source: SourceFileRecord) -> bool:
        return True

    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        return ParseResult(
            source_sha256=source.sha256,
            parser_name=self.name,
            parse_status="skipped",
            raw_text="",
            warnings=[f"Unsupported extension '{source.extension}', stored as binary metadata only."],
        )
