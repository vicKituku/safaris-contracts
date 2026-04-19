from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from ingestion.models import NormalizedRateRule, ParseResult, SourceFileRecord
from ingestion.normalizers import (
    detect_child_policy,
    normalize_currency,
    normalize_meal_plan,
    normalize_rate_unit,
    normalize_resident_category,
    parse_date_maybe,
    room_candidates,
    safe_float,
    slugify,
)

AMOUNT_PATTERN = re.compile(r"(?:USD|KES|KSH|KSHS|EUR|EURO|\$|€)?\s?([0-9]{2,}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)")
DATE_RANGE_PATTERN = re.compile(
    r"([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}).{0,15}?to.{0,15}?([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4})",
    flags=re.IGNORECASE,
)
SEASON_PATTERN = re.compile(r"(low season|mid season|high season|green season|peak season|festive)", flags=re.IGNORECASE)


def extract_rate_rules(source: SourceFileRecord, parse: ParseResult) -> Iterable[NormalizedRateRule]:
    text = parse.raw_text or source.relative_path
    destination = source.destination_name or "UNKNOWN"
    hotel = source.hotel_name or "UNKNOWN"

    destination_key = slugify(destination)
    hotel_key = slugify(hotel)

    amounts = [safe_float(m.group(1).replace(",", "")) for m in AMOUNT_PATTERN.finditer(text)]
    amounts = [a for a in amounts if a is not None]

    resident = normalize_resident_category(text)
    meal_plan = normalize_meal_plan(text)
    currency = normalize_currency(text)
    rate_unit = normalize_rate_unit(text)
    room_type = next(iter(room_candidates(text)), None)
    child_policy = detect_child_policy(text)

    valid_from: datetime | None = None
    valid_to: datetime | None = None
    range_match = DATE_RANGE_PATTERN.search(text)
    if range_match:
        valid_from = parse_date_maybe(range_match.group(1))
        valid_to = parse_date_maybe(range_match.group(2))

    season_match = SEASON_PATTERN.search(text)
    season_label = season_match.group(1).lower() if season_match else None

    contract_code = f"{hotel_key}:{source.sha256[:10]}"

    if amounts:
        for amount in amounts[:8]:
            yield NormalizedRateRule(
                hotel_key=hotel_key,
                destination_key=destination_key,
                contract_code=contract_code,
                resident_category=resident,
                meal_plan=meal_plan,
                room_type=room_type,
                occupancy=None,
                rate_amount=amount,
                currency=currency,
                rate_unit=rate_unit,
                season_label=season_label,
                valid_from=valid_from,
                valid_to=valid_to,
                child_policy=child_policy,
                supplements=[],
                source_evidence={
                    "relative_path": source.relative_path,
                    "parser": parse.parser_name,
                    "parse_status": parse.parse_status,
                },
                requires_manual_review=parse.parse_status != "parsed",
            )
    else:
        yield NormalizedRateRule(
            hotel_key=hotel_key,
            destination_key=destination_key,
            contract_code=contract_code,
            resident_category=resident,
            meal_plan=meal_plan,
            room_type=room_type,
            occupancy=None,
            rate_amount=None,
            currency=currency,
            rate_unit=rate_unit,
            season_label=season_label,
            valid_from=valid_from,
            valid_to=valid_to,
            child_policy=child_policy,
            supplements=[],
            source_evidence={
                "relative_path": source.relative_path,
                "parser": parse.parser_name,
                "parse_status": parse.parse_status,
                "reason": "No numeric rate amounts extracted",
            },
            requires_manual_review=True,
        )
