from __future__ import annotations

import logging
from dataclasses import asdict

from config import Settings
from ingestion.extractors import extract_rate_rules
from ingestion.models import IngestionIssue, NormalizedRateRule
from ingestion.mongo_loader import MongoLoader
from ingestion.parser_registry import ParserRegistry
from ingestion.reporter import generate_report
from ingestion.scanner import scan_repository
from ingestion.validator import validate_rules

logger = logging.getLogger(__name__)


def run_pipeline(settings: Settings, dry_run: bool = False) -> dict:
    registry = ParserRegistry(settings)
    logger.info("Scanning repository: %s", settings.repo_root)
    sources = list(scan_repository(settings.repo_root))
    source_lookup = {s.sha256: s for s in sources}

    logger.info("Found %s files", len(sources))
    parse_results = [registry.parse(source, max_chars=settings.max_text_chars) for source in sources]

    rules: list[NormalizedRateRule] = []
    for source, parse in zip(sources, parse_results, strict=True):
        rules.extend(extract_rate_rules(source, parse))

    issues: list[IngestionIssue] = validate_rules(rules)

    stats = {
        "files_scanned": len(sources),
        "parsed_records": len(parse_results),
        "rate_rules": len(rules),
        "issues": len(issues),
    }

    report_path = generate_report(settings.repo_root / "ingestion" / "reports", sources, parse_results, rules, issues)
    stats["report_path"] = str(report_path)

    if dry_run:
        logger.info("Dry run complete: %s", stats)
        return {"stats": stats, "sample_rules": [asdict(r) for r in rules[:10]]}

    loader = MongoLoader(settings.mongo_uri, settings.mongo_db)
    loader.ensure_indexes()
    run_id = loader.start_run(settings.run_label)
    try:
        loader.upsert_destinations_hotels(sources)
        loader.upsert_sources(sources)
        loader.upsert_parse_results(parse_results, source_lookup)
        loader.upsert_contracts_and_rates(rules)
        loader.insert_issues(run_id, issues)
        loader.finalize_run(run_id, stats, status="completed")
    except Exception as exc:
        loader.finalize_run(run_id, {**stats, "error": str(exc)}, status="failed")
        raise

    logger.info("Ingestion complete. Run ID: %s", run_id)
    return {"run_id": run_id, "stats": stats}
