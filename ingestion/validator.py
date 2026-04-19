from __future__ import annotations

from collections import defaultdict

from ingestion.models import IngestionIssue, NormalizedRateRule


KNOWN_MEAL_PLANS = {"BB", "HB", "FB", "AI", None}


def validate_rules(rules: list[NormalizedRateRule]) -> list[IngestionIssue]:
    issues: list[IngestionIssue] = []

    for rule in rules:
        src = rule.source_evidence.get("relative_path", "unknown")
        if rule.rate_amount is None:
            issues.append(
                IngestionIssue(
                    severity="warning",
                    code="missing_rate_amount",
                    message="No explicit numeric rate amount extracted.",
                    source_path=src,
                )
            )
        if rule.meal_plan not in KNOWN_MEAL_PLANS:
            issues.append(
                IngestionIssue(
                    severity="warning",
                    code="unknown_meal_plan",
                    message=f"Unrecognized meal plan: {rule.meal_plan}",
                    source_path=src,
                )
            )

        age_bands = rule.child_policy.get("age_bands", [])
        for band in age_bands:
            if band["from"] > band["to"]:
                issues.append(
                    IngestionIssue(
                        severity="error",
                        code="invalid_child_age_band",
                        message=f"Child age band invalid: {band}",
                        source_path=src,
                    )
                )

    by_key: dict[tuple[str, str, str, str | None], list[NormalizedRateRule]] = defaultdict(list)
    for rule in rules:
        by_key[(rule.hotel_key, rule.contract_code, rule.room_type or "", rule.resident_category)].append(rule)

    for key, grouped in by_key.items():
        dated = [r for r in grouped if r.valid_from and r.valid_to]
        dated.sort(key=lambda x: x.valid_from)
        for i in range(1, len(dated)):
            prev = dated[i - 1]
            curr = dated[i]
            if prev.valid_to and curr.valid_from and curr.valid_from <= prev.valid_to:
                issues.append(
                    IngestionIssue(
                        severity="warning",
                        code="overlapping_season",
                        message=f"Potential overlapping date ranges for key={key}",
                        source_path=curr.source_evidence.get("relative_path", "unknown"),
                    )
                )

    return issues
