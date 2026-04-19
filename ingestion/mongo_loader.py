from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from ingestion.models import IngestionIssue, NormalizedRateRule, ParseResult, SourceFileRecord


class MongoLoader:
    def __init__(self, mongo_uri: str, db_name: str) -> None:
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

    def ensure_indexes(self) -> None:
        self.db["source_files"].create_index("sha256", unique=True)
        self.db["source_files"].create_index([("relative_path", 1), ("modified_at", -1)])

        self.db["destinations"].create_index("destination_key", unique=True)
        self.db["hotels"].create_index("hotel_key", unique=True)
        self.db["hotels"].create_index([("destination_key", 1), ("canonical_name", 1)], unique=True)

        self.db["contracts"].create_index("contract_code", unique=True)
        self.db["contracts"].create_index([("hotel_key", 1), ("valid_from", 1), ("valid_to", 1)])

        self.db["rate_rules"].create_index(
            [
                ("hotel_key", 1),
                ("resident_category", 1),
                ("meal_plan", 1),
                ("room_type", 1),
                ("valid_from", 1),
                ("valid_to", 1),
            ]
        )
        self.db["rate_rules"].create_index("rule_hash", unique=True)

        self.db["ingestion_runs"].create_index("run_id", unique=True)
        self.db["ingestion_issues"].create_index([("run_id", 1), ("severity", 1), ("code", 1)])

    def start_run(self, run_label: str) -> str:
        run_id = datetime.now(UTC).strftime("run_%Y%m%dT%H%M%SZ")
        self.db["ingestion_runs"].insert_one(
            {
                "run_id": run_id,
                "run_label": run_label,
                "started_at": datetime.now(UTC),
                "status": "running",
                "stats": {},
            }
        )
        return run_id

    def finalize_run(self, run_id: str, stats: dict[str, Any], status: str = "completed") -> None:
        self.db["ingestion_runs"].update_one(
            {"run_id": run_id},
            {"$set": {"finished_at": datetime.now(UTC), "status": status, "stats": stats}},
        )

    def upsert_destinations_hotels(self, sources: list[SourceFileRecord]) -> None:
        destination_ops: list[UpdateOne] = []
        hotel_ops: list[UpdateOne] = []

        for src in sources:
            if src.destination_name:
                dest_key = src.destination_name.strip().lower()
                destination_ops.append(
                    UpdateOne(
                        {"destination_key": dest_key},
                        {"$set": {"destination_name": src.destination_name, "updated_at": datetime.now(UTC)}},
                        upsert=True,
                    )
                )
            if src.destination_name and src.hotel_name:
                dest_key = src.destination_name.strip().lower()
                hotel_key = src.hotel_name.strip().lower()
                hotel_ops.append(
                    UpdateOne(
                        {"hotel_key": hotel_key},
                        {
                            "$set": {
                                "canonical_name": src.hotel_name,
                                "destination_key": dest_key,
                                "updated_at": datetime.now(UTC),
                            }
                        },
                        upsert=True,
                    )
                )

        if destination_ops:
            self.db["destinations"].bulk_write(destination_ops, ordered=False)
        if hotel_ops:
            self.db["hotels"].bulk_write(hotel_ops, ordered=False)

    def upsert_sources(self, sources: list[SourceFileRecord]) -> None:
        col: Collection = self.db["source_files"]
        ops = []
        for src in sources:
            data = asdict(src)
            data["absolute_path"] = str(src.absolute_path)
            data["updated_at"] = datetime.now(UTC)
            ops.append(UpdateOne({"sha256": src.sha256}, {"$set": data}, upsert=True))
        if ops:
            col.bulk_write(ops, ordered=False)

    def upsert_parse_results(self, parse_results: list[ParseResult], source_lookup: dict[str, SourceFileRecord]) -> None:
        col = self.db["parsed_extractions"]
        ops = []
        for result in parse_results:
            src = source_lookup[result.source_sha256]
            doc = asdict(result)
            doc["relative_path"] = src.relative_path
            doc["updated_at"] = datetime.now(UTC)
            ops.append(UpdateOne({"source_sha256": result.source_sha256}, {"$set": doc}, upsert=True))
        if ops:
            col.bulk_write(ops, ordered=False)

    def upsert_contracts_and_rates(self, rules: list[NormalizedRateRule]) -> None:
        contracts_ops = []
        rate_ops = []
        for rule in rules:
            contracts_ops.append(
                UpdateOne(
                    {"contract_code": rule.contract_code},
                    {
                        "$set": {
                            "hotel_key": rule.hotel_key,
                            "destination_key": rule.destination_key,
                            "resident_category": rule.resident_category,
                            "valid_from": rule.valid_from,
                            "valid_to": rule.valid_to,
                            "updated_at": datetime.now(UTC),
                        }
                    },
                    upsert=True,
                )
            )

            rule_hash = f"{rule.contract_code}|{rule.room_type}|{rule.meal_plan}|{rule.rate_amount}|{rule.valid_from}|{rule.valid_to}|{rule.resident_category}"
            rate_ops.append(
                UpdateOne(
                    {"rule_hash": rule_hash},
                    {
                        "$set": {
                            **asdict(rule),
                            "rule_hash": rule_hash,
                            "updated_at": datetime.now(UTC),
                        }
                    },
                    upsert=True,
                )
            )

        if contracts_ops:
            self.db["contracts"].bulk_write(contracts_ops, ordered=False)
        if rate_ops:
            self.db["rate_rules"].bulk_write(rate_ops, ordered=False)

    def insert_issues(self, run_id: str, issues: list[IngestionIssue]) -> None:
        if not issues:
            return
        self.db["ingestion_issues"].insert_many(
            [{"run_id": run_id, **asdict(i), "created_at": datetime.now(UTC)} for i in issues]
        )
