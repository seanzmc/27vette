#!/usr/bin/env python3
"""Immutable ``workbook-changeset-1`` contract.

This module owns the workbook-changeset-1 contract: canonical
normalization, strict parsing, semantic fingerprinting, and conversion
to editor apply batches. The changeset is the single interchange
between change producers (editor UI, ingest wizard) and the workbook
editor apply path; payloads are validated and fingerprinted here so
consumers never re-interpret raw JSON.
"""

from __future__ import annotations

import copy
import hashlib
import json
import string

from corvette_form_generator.workbook_domain.registry import family_spec

SCHEMA_VERSION = "workbook-changeset-1"

_TOP_LEVEL_REQUIRED = frozenset({
    "schemaVersion",
    "source",
    "targets",
    "workbook",
    "sheetCreates",
    "rowChanges",
    "noops",
    "warningAcknowledgementsRequested",
    "bindings",
    "semanticFingerprint",
    "changeSetId",
})

_ROW_CHANGE_ALLOWED = frozenset({
    "action",
    "sheet",
    "family",
    "key",
    "fields",
    "provenance",
})

_SHEET_CREATE_REQUIRED = frozenset({"sheet", "family", "headersFrom"})

_ACTIONS = frozenset({"add", "update", "delete"})

_FINGERPRINT_EXCLUDED = frozenset({"changeSetId", "semanticFingerprint"})

_HEX_DIGITS = frozenset(string.hexdigits)


class ChangeSetError(ValueError):
    """Raised when a workbook-changeset-1 payload is invalid or stale."""


def canonical_json(value):
    """Serialize ``value`` deterministically (sorted keys, compact)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def changeset_fingerprint(payload):
    """SHA-256 hex of the canonical payload minus identity fields.

    Only the top-level ``changeSetId`` and ``semanticFingerprint`` keys
    are excluded. The caller's payload is never mutated.
    """
    body = {key: value for key, value in payload.items()
            if key not in _FINGERPRINT_EXCLUDED}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def parse_changeset(payload):
    """Validate a workbook-changeset-1 payload strictly.

    Returns a deep-copied normalized dict on success; raises
    ``ChangeSetError`` on any contract violation. Caller data is never
    mutated.
    """
    if not isinstance(payload, dict):
        raise ChangeSetError("changeset payload must be a JSON object")
    unknown = sorted(set(payload) - _TOP_LEVEL_REQUIRED)
    if unknown:
        raise ChangeSetError(f"unknown top-level fields: {unknown}")
    missing = sorted(_TOP_LEVEL_REQUIRED - set(payload))
    if missing:
        raise ChangeSetError(f"missing required top-level fields: {missing}")
    if payload["schemaVersion"] != SCHEMA_VERSION:
        raise ChangeSetError(
            f"unsupported schemaVersion: {payload['schemaVersion']!r}")
    _validate_targets(payload["targets"])
    _validate_workbook(payload["workbook"])
    _validate_sheet_creates(payload["sheetCreates"])
    _validate_row_changes(payload["rowChanges"])
    fingerprint = changeset_fingerprint(payload)
    if payload["semanticFingerprint"] != fingerprint:
        raise ChangeSetError(
            "semanticFingerprint does not match payload contents: "
            f"computed {fingerprint}, "
            f"stored {payload['semanticFingerprint']}")
    if payload["changeSetId"] != payload["semanticFingerprint"][:24]:
        raise ChangeSetError("changeSetId must equal semanticFingerprint[:24]")
    return copy.deepcopy(payload)


def _validate_targets(targets):
    if not isinstance(targets, list) or not targets:
        raise ChangeSetError("targets must be a non-empty list of strings")
    if not all(isinstance(target, str) for target in targets):
        raise ChangeSetError("targets must be a non-empty list of strings")
    if len(set(targets)) != len(targets):
        raise ChangeSetError("targets must not contain duplicates")
    if targets != sorted(targets):
        raise ChangeSetError("targets must be sorted")


def _validate_workbook(workbook):
    if not isinstance(workbook, dict):
        raise ChangeSetError("workbook must be an object")
    sha256 = workbook.get("sha256")
    if (not isinstance(sha256, str) or len(sha256) != 64
            or not all(char in _HEX_DIGITS for char in sha256)):
        raise ChangeSetError("workbook.sha256 must be exactly 64 hex characters")
    if not isinstance(workbook.get("mtimeNs"), str):
        raise ChangeSetError("workbook.mtimeNs must be a string")


def _validate_family(name, ctx):
    try:
        return family_spec(name)
    except (KeyError, TypeError) as exc:
        raise ChangeSetError(f"{ctx}: unknown family: {name!r}") from exc


def _validate_sheet_creates(sheet_creates):
    if not isinstance(sheet_creates, list):
        raise ChangeSetError("sheetCreates must be a list")
    for index, entry in enumerate(sheet_creates):
        ctx = f"sheetCreates[{index}]"
        if not isinstance(entry, dict):
            raise ChangeSetError(f"{ctx} must be an object")
        unknown = sorted(set(entry) - _SHEET_CREATE_REQUIRED)
        if unknown:
            raise ChangeSetError(f"{ctx} unknown fields: {unknown}")
        missing = sorted(_SHEET_CREATE_REQUIRED - set(entry))
        if missing:
            raise ChangeSetError(f"{ctx} missing fields: {missing}")
        if not all(isinstance(entry[key], str) for key in _SHEET_CREATE_REQUIRED):
            raise ChangeSetError(
                f"{ctx} sheet, family, and headersFrom must be strings")
        _validate_family(entry["family"], ctx)


def _validate_row_changes(row_changes):
    if not isinstance(row_changes, list):
        raise ChangeSetError("rowChanges must be a list")
    seen_keys = set()
    for index, change in enumerate(row_changes):
        ctx = f"rowChanges[{index}]"
        if not isinstance(change, dict):
            raise ChangeSetError(f"{ctx} must be an object")
        unknown = sorted(set(change) - _ROW_CHANGE_ALLOWED)
        if unknown:
            raise ChangeSetError(f"{ctx} unknown row change fields: {unknown}")
        missing = sorted(_ROW_CHANGE_ALLOWED - set(change))
        if missing:
            raise ChangeSetError(f"{ctx} missing row change fields: {missing}")
        action = change["action"]
        if action not in _ACTIONS:
            raise ChangeSetError(f"{ctx} invalid action: {action!r}")
        spec = _validate_family(change["family"], ctx)
        key = change["key"]
        if not isinstance(key, dict) or set(key) != set(spec["key"]):
            raise ChangeSetError(
                f"{ctx} key columns must exactly match family key "
                f"{spec['key']!r}")
        _validate_fields(change["fields"], action, ctx)
        _validate_provenance(change["provenance"], ctx)
        row_key = (change["sheet"], canonical_json(key))
        if row_key in seen_keys:
            raise ChangeSetError(
                f"{ctx} duplicate row key: {change['sheet']!r} {key!r}")
        seen_keys.add(row_key)


def _validate_fields(fields, action, ctx):
    if not isinstance(fields, dict):
        raise ChangeSetError(f"{ctx} fields must be an object")
    for column, pair in fields.items():
        if not isinstance(pair, dict) or set(pair) != {"before", "after"}:
            raise ChangeSetError(
                f"{ctx} field {column!r} must be an object with exactly "
                "before and after")
        before, after = pair["before"], pair["after"]
        if canonical_json(before) == canonical_json(after):
            raise ChangeSetError(
                f"{ctx} field {column!r} is an unchanged field pair")
        if action == "add" and before is not None:
            raise ChangeSetError(
                f"{ctx} add field {column!r} must have a null before value")
        if action == "delete" and after is not None:
            raise ChangeSetError(
                f"{ctx} delete field {column!r} must have a null after value")


def _validate_provenance(provenance, ctx):
    if not isinstance(provenance, list) or not provenance:
        raise ChangeSetError(
            f"{ctx} provenance must be a non-empty list of objects")
    for entry in provenance:
        if not isinstance(entry, dict) or "kind" not in entry or "id" not in entry:
            raise ChangeSetError(
                f"{ctx} provenance entries must be objects with kind and id")


def _find_row(rows, key_columns, key):
    for row in rows:
        if all(row.get(column) == key.get(column) for column in key_columns):
            return row
    return None


def _check_before_values(change, current, ctx):
    for column, pair in change["fields"].items():
        actual = current.get(column)
        expected = pair["before"]
        bool_type_mismatch = (
            isinstance(actual, bool) or isinstance(expected, bool)
        ) and type(actual) is not type(expected)
        if bool_type_mismatch or actual != expected:
            raise ChangeSetError(
                f"{ctx} stale before value for field {column!r}: "
                f"changeset expects {expected!r}, "
                f"workbook has {actual!r}")


def changeset_to_editor_batch(changeset, extract):
    """Convert a parsed changeset into an ``editor_ops.apply_batch`` batch.

    Precondition: ``changeset`` must already have passed
    ``parse_changeset()``; this function does not re-validate the contract
    and raises raw ``KeyError`` for structurally impossible input.

    ``extract`` is the extracted workbook rows mapping
    (``{"sheets": {sheet: {"headers": [...], "rows": [...]}}}``) used to
    resolve current rows and verify stale-before freshness. Before values
    compare with Python ``!=`` against extracted cell values, so producers
    must emit before values matching workbook storage conventions (some
    sheets store Boolean columns as the text ``"True"``/``"False"``;
    ``"True" != True`` would fail closed with a stale-before error).

    ``source``, ``noops``, ``warningAcknowledgementsRequested``, and
    ``bindings`` are carried by the contract but not interpreted here. Every
    ChangeSet batch forces real Excel booleans so activating a previously
    inactive scaffold cannot preserve legacy text booleans into an active
    model source sheet.

    Emitted items are deep-copied from the changeset: mutating the returned
    batch never alters the parsed changeset it was derived from.
    """
    items = []
    for create in changeset.get("sheetCreates", []):
        items.append({
            "action": "create_sheet",
            "sheet": create["sheet"],
            "family": create["family"],
            "headersFrom": create["headersFrom"],
        })
    sheets = extract.get("sheets", {})
    for index, change in enumerate(changeset.get("rowChanges", [])):
        ctx = f"rowChanges[{index}]"
        sheet = change["sheet"]
        key = change["key"]
        action = change["action"]
        key_columns = family_spec(change["family"])["key"]
        sheet_data = sheets.get(sheet)
        rows = sheet_data.get("rows", []) if isinstance(sheet_data, dict) else []
        current = _find_row(rows, key_columns, key)
        if action == "add":
            if current is not None:
                raise ChangeSetError(
                    f"{ctx} add key already exists: {sheet!r} {key!r}")
            items.append({
                "action": "add",
                "sheet": sheet,
                "key": copy.deepcopy(key),
                "row": copy.deepcopy({column: pair["after"]
                                      for column, pair in change["fields"].items()}),
            })
            continue
        if sheet_data is None:
            raise ChangeSetError(
                f"{ctx} {action} targets missing sheet: {sheet!r}")
        if current is None:
            raise ChangeSetError(
                f"{ctx} {action} row not found: {sheet!r} {key!r}")
        _check_before_values(change, current, ctx)
        if action == "update":
            items.append({
                "action": "update",
                "sheet": sheet,
                "key": copy.deepcopy(key),
                "row": copy.deepcopy({column: pair["after"]
                                      for column, pair in change["fields"].items()}),
            })
        else:  # delete
            items.append({
                "action": "delete",
                "sheet": sheet,
                "key": copy.deepcopy(key),
            })
    return {
        "workbookMtimeNs": changeset["workbook"]["mtimeNs"],
        "workbookSha256": changeset["workbook"]["sha256"],
        "forceTypedBools": True,
        "items": items,
    }
