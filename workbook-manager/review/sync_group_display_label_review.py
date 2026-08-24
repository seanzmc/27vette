#!/usr/bin/env python3
"""Synchronize reviewed group-label CSV decisions into the JSON companion.

The CSV is the human-review surface. This command validates its decision fields
against the original JSON inventory, restores the specification's stable source
ordering, and writes both artifacts as exact decision companions without
rebinding them to the post-migration workbook.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "workbook-manager" / "review"
CSV_PATH = REVIEW_DIR / "group-display-label-review.csv"
JSON_PATH = REVIEW_DIR / "group-display-label-review.json"
sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.workbook_domain.registry import (  # noqa: E402
    GROUP_DISPLAY_LABEL_HASH_SUFFIX_PATTERN,
    GROUP_DISPLAY_LABEL_MAX_LENGTH,
    GROUP_DISPLAY_LABEL_MIN_LENGTH,
    GROUP_DISPLAY_LABEL_PLACEHOLDERS,
)

VALID_STATUSES = {"pending", "approved", "revise", "not_customer_rendered"}
HASH_SUFFIX = re.compile(GROUP_DISPLAY_LABEL_HASH_SUFFIX_PATTERN, re.IGNORECASE)
DECISION_FIELDS = (
    "proposed_display_label",
    "review_status",
    "reviewer_note",
    "audience",
)


def identity(row: dict) -> tuple[str, str, str]:
    return row["model_key"], row["group_type"], row["group_id"]


def stable_key(row: dict) -> tuple[str, str, str, int, str]:
    sheet, row_number = row["source_sheet_row"].rsplit("!", 1)
    return row["model_key"], row["group_type"], sheet, int(row_number), row["group_id"]


def parse_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"expected TRUE or FALSE, got {value!r}")


def csv_text(value) -> str:
    """Render a JSON record value exactly as the generator wrote it to CSV."""
    if isinstance(value, bool):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def assert_evidence_unchanged(row: dict, record: dict) -> None:
    """Reject edits to any non-decision field.

    Only the decision fields and `customer_visible` are copied into the JSON
    companion, so an edit to an evidence column such as `active`,
    `member_count`, `notes`, or `current_fallback_label` would otherwise be
    written back to the CSV while the JSON kept the generated value, leaving
    two artifacts that are no longer exact companions.
    """
    key = identity(row)
    changed = []
    for field, value in row.items():
        if field in DECISION_FIELDS or field == "customer_visible":
            continue
        if field not in record:
            continue
        generated = record[field]
        if isinstance(generated, bool):
            # A spreadsheet round-trip rewrites `true` as `TRUE`; the artifact
            # contract already reads booleans case-insensitively, so compare
            # the value rather than the text.
            try:
                edited = parse_bool(value)
            except ValueError:
                changed.append(f"{field}: {generated!r} -> {value!r}")
                continue
            if edited != generated:
                changed.append(f"{field}: {generated!r} -> {value!r}")
            continue
        if value != csv_text(generated):
            changed.append(f"{field}: {generated!r} -> {value!r}")
    if changed:
        raise ValueError(
            f"{key}: evidence fields are generated and must not be edited; "
            "regenerate the review artifacts instead of hand-editing them "
            f"({'; '.join(sorted(changed))})"
        )


def validate_decision(row: dict) -> None:
    key = identity(row)
    status = row["review_status"].strip().casefold()
    label = row["proposed_display_label"]
    if status not in VALID_STATUSES:
        raise ValueError(f"{key}: invalid review_status {status!r}")
    row["review_status"] = status
    if status != "approved":
        return
    if label != label.strip() or "\n" in label or "\r" in label:
        raise ValueError(f"{key}: approved label must be trimmed and single-line")
    if not GROUP_DISPLAY_LABEL_MIN_LENGTH <= len(label) <= GROUP_DISPLAY_LABEL_MAX_LENGTH:
        raise ValueError(
            f"{key}: approved label length must be "
            f"{GROUP_DISPLAY_LABEL_MIN_LENGTH}-{GROUP_DISPLAY_LABEL_MAX_LENGTH}"
        )
    if label == row["group_id"] or label in GROUP_DISPLAY_LABEL_PLACEHOLDERS:
        raise ValueError(f"{key}: approved label cannot be an ID or fallback placeholder")
    hash_match = HASH_SUFFIX.search(row["group_id"])
    if hash_match and hash_match.group(1).casefold() in label.casefold():
        raise ValueError(f"{key}: approved label contains the canonical hash token")


def main() -> None:
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or ())
        csv_rows = list(reader)
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_rows = payload["records"]

    csv_keys = [identity(row) for row in csv_rows]
    json_by_key = {identity(row): row for row in json_rows}
    if len(csv_keys) != len(set(csv_keys)):
        raise ValueError("review CSV contains duplicate group identities")
    if len(json_by_key) != len(json_rows):
        raise ValueError("review JSON contains duplicate group identities")
    if set(csv_keys) != set(json_by_key):
        raise ValueError("review CSV identity set differs from the generated JSON inventory")

    source_sha = payload["source_workbook_sha256"]
    schema_version = payload["artifact_schema_version"]
    for row in csv_rows:
        if row["source_workbook_sha256"] != source_sha:
            raise ValueError(f"{identity(row)}: source workbook binding changed")
        if row["artifact_schema_version"] != schema_version:
            raise ValueError(f"{identity(row)}: artifact schema version changed")
        assert_evidence_unchanged(row, json_by_key[identity(row)])
        validate_decision(row)

    csv_rows.sort(key=stable_key)
    synchronized_records = []
    for csv_row in csv_rows:
        record = dict(json_by_key[identity(csv_row)])
        for field in DECISION_FIELDS:
            record[field] = csv_row[field]
        record["customer_visible"] = parse_bool(csv_row["customer_visible"])
        synchronized_records.append(record)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)

    synchronized_payload = {
        **payload,
        "record_count": len(synchronized_records),
        "records": synchronized_records,
    }
    JSON_PATH.write_text(
        json.dumps(synchronized_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"synchronized {len(synchronized_records)} reviewed decisions; "
        f"source workbook sha256={source_sha}"
    )


if __name__ == "__main__":
    main()
