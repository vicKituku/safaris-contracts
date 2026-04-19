from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ingestion.models import IngestionIssue, NormalizedRateRule, ParseResult, SourceFileRecord


def generate_report(
    report_dir: Path,
    sources: list[SourceFileRecord],
    parse_results: list[ParseResult],
    rules: list[NormalizedRateRule],
    issues: list[IngestionIssue],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ext_counts = Counter(s.extension for s in sources)
    parse_counts = Counter(p.parse_status for p in parse_results)
    issue_counts = Counter(i.code for i in issues)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_files": len(sources),
        "file_types": ext_counts,
        "parse_status_counts": parse_counts,
        "total_rules": len(rules),
        "issues": issue_counts,
        "sample_issues": [asdict(i) for i in issues[:30]],
    }

    out_path = report_dir / f"ingestion_report_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return out_path
