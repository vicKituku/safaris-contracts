from __future__ import annotations

from abc import ABC, abstractmethod

from ingestion.models import ParseResult, SourceFileRecord


class BaseParser(ABC):
    name = "base"

    @abstractmethod
    def can_parse(self, source: SourceFileRecord) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: SourceFileRecord, max_chars: int) -> ParseResult:
        raise NotImplementedError
