from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SourceFileRecord:
    relative_path: str
    absolute_path: Path
    extension: str
    mime_hint: str
    file_size: int
    modified_at: datetime
    sha256: str
    destination_name: str | None
    hotel_name: str | None


@dataclass
class ParseResult:
    source_sha256: str
    parser_name: str
    parse_status: str
    raw_text: str = ""
    pages: int | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class NormalizedRateRule:
    hotel_key: str
    destination_key: str
    contract_code: str
    resident_category: str | None
    meal_plan: str | None
    room_type: str | None
    occupancy: str | None
    rate_amount: float | None
    currency: str | None
    rate_unit: str | None
    season_label: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    child_policy: dict[str, Any] = field(default_factory=dict)
    supplements: list[dict[str, Any]] = field(default_factory=list)
    source_evidence: dict[str, Any] = field(default_factory=dict)
    requires_manual_review: bool = False


@dataclass
class IngestionIssue:
    severity: str
    code: str
    message: str
    source_path: str
    context: dict[str, Any] = field(default_factory=dict)
