# Kenya Hotels Pricing Ingestion & MongoDB Data Model

## 1) Repository understanding and findings

- Dataset root is organized primarily as `DESTINATION/HOTEL/...files` with occasional deeper category subfolders.
- Total files scanned: **604**.
- Dominant format is **PDF** (contracts/rates): 476 files, then DOCX notes/terms (58), JPG/JPEG/PNG images/posters/rate cards (68), plus ZIP and MP4 assets.
- Pricing-bearing files are mostly PDFs and some image-based rate cards. DOCX files often carry terms/commission notes, and images may contain poster-style offers.
- Data quality observations:
  - Duplicate-like filenames and near-duplicates (e.g., "(1)", "copy", "updated").
  - Inconsistent naming for destinations/hotels and resident classes.
  - Mixed year ranges (2024–2027) and ad-hoc seasonal labels (low/high/green/festive).
  - Some files are clearly non-pricing collateral (factsheets/photos/video) but still retained for source traceability.

## 2) Key assumptions and data issues

- Folder name first segment is treated as canonical destination candidate.
- Second segment is treated as canonical hotel candidate.
- Not every file can be parsed deterministically (scanned PDFs, posters, photo-only assets).
- Rates are extracted conservatively; ambiguous text is flagged for manual review.
- All extracted rules retain source path + parser status for auditability.

## 3) Proposed MongoDB database design

Database: `kenya_hotels_pricing`

Collections:
- `destinations`: canonical destination dimension.
- `hotels`: canonical hotel dimension + destination linkage.
- `source_files`: immutable-ish source snapshot metadata + hash for idempotency.
- `parsed_extractions`: parser output (text, warnings, errors).
- `contracts`: logical commercial contract envelope per source hash/hotel.
- `rate_rules`: pricing-ready normalized atomic rules.
- `ingestion_runs`: ETL run headers.
- `ingestion_issues`: quality findings and validation warnings/errors.

## 4) Collection-by-collection schema details

### `destinations`
- `destination_key` (unique, lowercase key)
- `destination_name`
- `updated_at`

### `hotels`
- `hotel_key` (unique)
- `canonical_name`
- `destination_key` (ref-like)
- `updated_at`

### `source_files`
- `sha256` (unique)
- `relative_path`, `absolute_path`
- `extension`, `mime_hint`, `file_size`, `modified_at`
- `destination_name`, `hotel_name`
- `updated_at`

### `parsed_extractions`
- `source_sha256` (upsert key)
- `relative_path`
- `parser_name`, `parse_status`, `raw_text`, `pages`
- `warnings[]`, `errors[]`
- `updated_at`

### `contracts`
- `contract_code` (unique)
- `hotel_key`, `destination_key`
- `resident_category`
- `valid_from`, `valid_to`
- `updated_at`

### `rate_rules`
- `rule_hash` (unique idempotent key)
- `hotel_key`, `destination_key`, `contract_code`
- `resident_category`, `meal_plan`, `room_type`, `occupancy`
- `rate_amount`, `currency`, `rate_unit`
- `season_label`, `valid_from`, `valid_to`
- `child_policy` (age bands, free child clauses)
- `supplements[]`
- `source_evidence` (path/parser/status)
- `requires_manual_review`
- `updated_at`

### `ingestion_runs`
- `run_id` (unique)
- `run_label`, `started_at`, `finished_at`, `status`
- `stats` summary payload

### `ingestion_issues`
- `run_id`
- `severity`, `code`, `message`, `source_path`, `context`
- `created_at`

## 5) Index strategy

- Unique: `source_files.sha256`, `destinations.destination_key`, `hotels.hotel_key`, `contracts.contract_code`, `rate_rules.rule_hash`, `ingestion_runs.run_id`.
- Query acceleration:
  - `rate_rules` compound: `(hotel_key,resident_category,meal_plan,room_type,valid_from,valid_to)`
  - `hotels` compound: `(destination_key,canonical_name)`
  - `contracts` compound: `(hotel_key,valid_from,valid_to)`

## 6) Deterministic pricing support

Future pricing engine flow:
1. Resolve destination -> candidate hotels via `hotels.destination_key`.
2. Select active `rate_rules` by travel date in `[valid_from, valid_to]`.
3. Filter by resident class, meal plan, room type, occupancy.
4. Apply child policy and supplements explicitly from `rate_rules` payload.
5. Return quote with `source_evidence` for audit trail.

## 7) Parsing/normalization strategy

- PDF: text extraction via `pypdf`; if no text, mark unparsed/manual review.
- DOCX: paragraph extraction via `python-docx`.
- Images: metadata extraction always; OCR optional via `pytesseract` (`ENABLE_OCR=true`).
- Unsupported (zip/mp4/etc): metadata only + warning.
- Normalization includes: meal plan mapping, resident category mapping, currency normalization, rate unit inference, room keyword detection, child age-band parsing.

## 8) Validation/reporting strategy

Implemented checks:
- missing numeric rate amount
- unknown meal plan mapping
- impossible child age band (`from > to`)
- potential overlapping seasonal date ranges per contract/room/resident tuple

JSON run report written under `ingestion/reports/` with file-type counts, parse outcomes, issue tallies, and sample issues.

## 9) Idempotency and re-ingestion

- Source hash (`sha256`) acts as immutable file identity.
- Upserts used across dimensions/facts (`source_files`, `parsed_extractions`, `contracts`, `rate_rules`).
- `rule_hash` prevents duplicate normalized rule inserts across reruns.
- Each pipeline run logged in `ingestion_runs` with status and stats.
