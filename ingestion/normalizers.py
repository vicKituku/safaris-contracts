from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser

MEAL_PLAN_MAP = {
    "BED & BREAKFAST": "BB",
    "B&B": "BB",
    "BB": "BB",
    "HALF BOARD": "HB",
    "HB": "HB",
    "FULL BOARD": "FB",
    "FB": "FB",
    "ALL INCLUSIVE": "AI",
    "AI": "AI",
}

RESIDENT_MAP = {
    "RESIDENT": "resident",
    "RESIDENTS": "resident",
    "CITIZEN": "citizen",
    "EAST AFRICAN": "ea_resident",
    "NON RESIDENT": "non_resident",
    "NON-RESIDENT": "non_resident",
    "INTERNATIONAL": "non_resident",
}

RATE_UNIT_KEYWORDS = {
    "PER PERSON PER NIGHT": "pppn",
    "PER PERSON": "pp",
    "PER ROOM PER NIGHT": "prpn",
    "PER ROOM": "pr",
    "FULL BOARD": "package",
}


def slugify(value: str) -> str:
    txt = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt.lower()).strip("-")
    return txt


def normalize_meal_plan(text: str) -> str | None:
    u = text.upper()
    for key, val in MEAL_PLAN_MAP.items():
        if key in u:
            return val
    return None


def normalize_resident_category(text: str) -> str | None:
    u = text.upper()
    for key, val in RESIDENT_MAP.items():
        if key in u:
            return val
    return None


def normalize_rate_unit(text: str) -> str | None:
    u = text.upper()
    for key, val in RATE_UNIT_KEYWORDS.items():
        if key in u:
            return val
    return None


def parse_date_maybe(value: str) -> datetime | None:
    try:
        return date_parser.parse(value, dayfirst=True, fuzzy=True)
    except Exception:
        return None


def normalize_currency(text: str) -> str | None:
    u = text.upper()
    if "USD" in u or "$" in text:
        return "USD"
    if "KES" in u or "KSH" in u or "KSHS" in u:
        return "KES"
    if "EUR" in u or "EURO" in u or "€" in text:
        return "EUR"
    return None


def safe_float(value: str) -> float | None:
    cleaned = re.sub(r"[^0-9.]", "", value)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def room_candidates(text: str) -> list[str]:
    rooms = []
    for keyword in ["single", "double", "twin", "triple", "family", "suite", "villa", "tent"]:
        if re.search(rf"\b{keyword}\b", text, flags=re.IGNORECASE):
            rooms.append(keyword)
    return sorted(set(rooms))


def detect_child_policy(text: str) -> dict[str, Any]:
    policy: dict[str, Any] = {}
    age_match = re.findall(r"child(?:ren)?[^\n]{0,80}?([0-9]{1,2})\s*[-to]{1,3}\s*([0-9]{1,2})", text, flags=re.IGNORECASE)
    if age_match:
        policy["age_bands"] = [{"from": int(a), "to": int(b)} for a, b in age_match]
    if re.search(r"child(?:ren)?.{0,40}?free", text, flags=re.IGNORECASE):
        policy["free_child_clause"] = True
    return policy
