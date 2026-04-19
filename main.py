from __future__ import annotations

import argparse
import json

from config import settings
from ingestion.logging_utils import configure_logging
from ingestion.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kenya hotel contracts ingestion pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run parsers/normalizers without writing to MongoDB")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging()
    result = run_pipeline(settings, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
