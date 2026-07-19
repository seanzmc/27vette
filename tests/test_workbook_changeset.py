#!/usr/bin/env python3
"""Tests for the workbook-changeset-1 contract (workbook_domain.changeset)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.workbook_domain.changeset import (  # noqa: E402
    ChangeSetError,
    canonical_json,
    changeset_fingerprint,
    changeset_to_editor_batch,
    parse_changeset,
)


def sample_changeset():
    payload = {
        "schemaVersion": "workbook-changeset-1",
        "source": {"kind": "editor", "runId": "test-run"},
        "targets": ["stingray"],
        "workbook": {"sha256": "a" * 64, "mtimeNs": "123"},
        "sheetCreates": [],
        "rowChanges": [{
            "action": "update",
            "sheet": "stingray_options",
            "family": "options",
            "key": {"option_id": "opt_1"},
            "fields": {"price": {"before": 100, "after": 200}},
            "provenance": [{"kind": "editor", "id": "field:price"}],
        }],
        "noops": [],
        "warningAcknowledgementsRequested": [],
        "bindings": {},
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return payload


def _resign(payload):
    """Recompute freshness identity fields after a structural mutation."""
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return payload


def _mutate(payload, fn):
    mutant = copy.deepcopy(payload)
    fn(mutant)
    return _resign(mutant)


def _extract():
    return {"sheets": {"stingray_options": {
        "headers": ["option_id", "price"],
        "rows": [{"option_id": "opt_1", "price": 100}],
    }}}


def _delete_payload():
    payload = sample_changeset()
    payload["rowChanges"] = [{
        "action": "delete",
        "sheet": "stingray_options",
        "family": "options",
        "key": {"option_id": "opt_1"},
        "fields": {"price": {"before": 100, "after": None}},
        "provenance": [{"kind": "editor", "id": "row:opt_1"}],
    }]
    return _resign(payload)


def _add_payload(key_option_id="opt_2"):
    payload = sample_changeset()
    payload["rowChanges"] = [{
        "action": "add",
        "sheet": "stingray_options",
        "family": "options",
        "key": {"option_id": key_option_id},
        "fields": {
            "price": {"before": None, "after": 300},
            "label": {"before": None, "after": "New"},
        },
        "provenance": [{"kind": "editor", "id": "row:new"}],
    }]
    return _resign(payload)


# ── Plan-specified verbatim tests ─────────────────────────────────────

def test_fingerprint_ignores_mapping_order_but_not_semantics():
    payload = sample_changeset()
    reordered = copy.deepcopy(payload)
    reordered["source"] = {"runId": "test-run", "kind": "editor"}
    assert changeset_fingerprint(reordered) == payload["semanticFingerprint"]
    reordered["rowChanges"][0]["fields"]["price"]["after"] = 201
    assert changeset_fingerprint(reordered) != payload["semanticFingerprint"]


def test_update_emits_only_changed_fields_and_checks_before_value():
    parsed = parse_changeset(sample_changeset())
    extract = {"sheets": {"stingray_options": {
        "headers": ["option_id", "price"],
        "rows": [{"option_id": "opt_1", "price": 100}],
    }}}
    batch = changeset_to_editor_batch(parsed, extract)
    assert batch["items"] == [{
        "action": "update",
        "sheet": "stingray_options",
        "key": {"option_id": "opt_1"},
        "row": {"price": 200},
    }]
    extract["sheets"]["stingray_options"]["rows"][0]["price"] = 150
    with pytest.raises(ChangeSetError, match="before value"):
        changeset_to_editor_batch(parsed, extract)


# ── Fingerprint / canonicalization ────────────────────────────────────

def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": {"d": True, "c": None}}) == (
        '{"a":{"c":null,"d":true},"b":1}'
    )


def test_fingerprint_excludes_id_fields_and_never_mutates():
    payload = sample_changeset()
    snapshot = copy.deepcopy(payload)
    stripped = {k: v for k, v in payload.items()
                if k not in ("changeSetId", "semanticFingerprint")}
    assert changeset_fingerprint(stripped) == payload["semanticFingerprint"]
    assert changeset_fingerprint(payload) == payload["semanticFingerprint"]
    assert payload == snapshot


# ── Parsing: acceptance ───────────────────────────────────────────────

def test_parse_returns_independent_deepcopy_without_mutating_input():
    payload = sample_changeset()
    snapshot = copy.deepcopy(payload)
    parsed = parse_changeset(payload)
    assert parsed == payload
    assert parsed is not payload
    parsed["rowChanges"][0]["fields"]["price"]["after"] = 999
    assert payload["rowChanges"][0]["fields"]["price"]["after"] == 200
    assert payload == snapshot


# ── Parsing: Step 3 rejection rules ───────────────────────────────────

def test_rejects_unknown_top_level_field():
    payload = _mutate(sample_changeset(), lambda p: p.update({"extraField": True}))
    with pytest.raises(ChangeSetError, match="unknown top-level"):
        parse_changeset(payload)


def test_rejects_missing_required_top_level_field():
    required = [
        "schemaVersion", "source", "targets", "workbook", "sheetCreates",
        "rowChanges", "noops", "warningAcknowledgementsRequested", "bindings",
        "semanticFingerprint", "changeSetId",
    ]
    for key in required:
        payload = sample_changeset()
        del payload[key]
        with pytest.raises(ChangeSetError, match="missing required"):
            parse_changeset(payload)


def test_rejects_wrong_schema_version():
    payload = _mutate(
        sample_changeset(),
        lambda p: p.update({"schemaVersion": "workbook-changeset-2"}),
    )
    with pytest.raises(ChangeSetError, match="schemaVersion"):
        parse_changeset(payload)


def test_rejects_unknown_row_change_field():
    payload = _mutate(
        sample_changeset(), lambda p: p["rowChanges"][0].update({"note": "x"}))
    with pytest.raises(ChangeSetError, match="row change"):
        parse_changeset(payload)


def test_rejects_invalid_action():
    payload = _mutate(
        sample_changeset(), lambda p: p["rowChanges"][0].update({"action": "move"}))
    with pytest.raises(ChangeSetError, match="action"):
        parse_changeset(payload)


def test_rejects_duplicate_row_keys_regardless_of_key_order():
    payload = sample_changeset()
    payload["rowChanges"] = [
        {
            "action": "update",
            "sheet": "stingray_ovs",
            "family": "ovs",
            "key": {"option_id": "opt_1", "variant_id": "var_1"},
            "fields": {"status": {"before": "standard", "after": "unavailable"}},
            "provenance": [{"kind": "editor", "id": "f:status"}],
        },
        {
            "action": "update",
            "sheet": "stingray_ovs",
            "family": "ovs",
            "key": {"variant_id": "var_1", "option_id": "opt_1"},
            "fields": {"status": {"before": "standard", "after": "available"}},
            "provenance": [{"kind": "editor", "id": "f:status2"}],
        },
    ]
    with pytest.raises(ChangeSetError, match="duplicate"):
        parse_changeset(_resign(payload))


def test_rejects_unchanged_field_pair():
    payload = _mutate(
        sample_changeset(),
        lambda p: p["rowChanges"][0]["fields"]["price"].update({"after": 100}),
    )
    with pytest.raises(ChangeSetError, match="unchanged"):
        parse_changeset(payload)


def test_rejects_missing_or_empty_provenance():
    base = sample_changeset()
    missing = copy.deepcopy(base)
    del missing["rowChanges"][0]["provenance"]
    cases = [
        _resign(missing),
        _mutate(base, lambda p: p["rowChanges"][0].update({"provenance": []})),
        _mutate(base, lambda p: p["rowChanges"][0].update(
            {"provenance": [{"kind": "editor"}]})),
        _mutate(base, lambda p: p["rowChanges"][0].update(
            {"provenance": [{"id": "x"}]})),
        _mutate(base, lambda p: p["rowChanges"][0].update(
            {"provenance": "editor"})),
    ]
    for payload in cases:
        with pytest.raises(ChangeSetError, match="provenance"):
            parse_changeset(payload)


def test_rejects_unknown_family():
    payload = _mutate(
        sample_changeset(),
        lambda p: p["rowChanges"][0].update({"family": "not_a_family"}),
    )
    with pytest.raises(ChangeSetError, match="family"):
        parse_changeset(payload)


def test_rejects_key_columns_mismatching_family_key():
    base = sample_changeset()
    extra = _mutate(base, lambda p: p["rowChanges"][0].update(
        {"key": {"option_id": "opt_1", "extra": 1}}))
    missing = _mutate(base, lambda p: p["rowChanges"][0].update({"key": {}}))
    for payload in (extra, missing):
        with pytest.raises(ChangeSetError, match="key"):
            parse_changeset(payload)


def test_rejects_field_pair_shape_violations():
    base = sample_changeset()
    cases = [
        _mutate(base, lambda p: p["rowChanges"][0]["fields"].update(
            {"price": {"before": 100}})),
        _mutate(base, lambda p: p["rowChanges"][0]["fields"].update(
            {"price": {"before": 100, "after": 200, "note": "x"}})),
        _mutate(base, lambda p: p["rowChanges"][0]["fields"].update(
            {"price": [100, 200]})),
    ]
    for payload in cases:
        with pytest.raises(ChangeSetError, match="before"):
            parse_changeset(payload)


def test_rejects_add_with_non_null_before():
    payload = _mutate(
        sample_changeset(), lambda p: p["rowChanges"][0].update({"action": "add"}))
    with pytest.raises(ChangeSetError, match="add"):
        parse_changeset(payload)


def test_rejects_delete_with_non_null_after():
    payload = _mutate(
        sample_changeset(),
        lambda p: p["rowChanges"][0].update({"action": "delete"}),
    )
    with pytest.raises(ChangeSetError, match="delete"):
        parse_changeset(payload)


def test_rejects_invalid_workbook_sha256():
    base = sample_changeset()
    cases = [
        _mutate(base, lambda p: p["workbook"].update({"sha256": "abc"})),
        _mutate(base, lambda p: p["workbook"].update({"sha256": "g" * 64})),
        _mutate(base, lambda p: p["workbook"].update({"sha256": 5})),
    ]
    for payload in cases:
        with pytest.raises(ChangeSetError, match="sha256"):
            parse_changeset(payload)


def test_rejects_non_string_workbook_mtime():
    payload = _mutate(
        sample_changeset(), lambda p: p["workbook"].update({"mtimeNs": 123}))
    with pytest.raises(ChangeSetError, match="mtimeNs"):
        parse_changeset(payload)


def test_rejects_unsorted_empty_duplicate_or_non_string_targets():
    base = sample_changeset()
    cases = [
        _mutate(base, lambda p: p.update({"targets": []})),
        _mutate(base, lambda p: p.update({"targets": ["z06", "stingray"]})),
        _mutate(base, lambda p: p.update({"targets": ["stingray", "stingray"]})),
        _mutate(base, lambda p: p.update({"targets": ["stingray", 7]})),
    ]
    for payload in cases:
        with pytest.raises(ChangeSetError, match="targets"):
            parse_changeset(payload)


def test_rejects_semantic_fingerprint_mismatch():
    payload = sample_changeset()
    payload["semanticFingerprint"] = "0" * 64
    with pytest.raises(ChangeSetError, match="semanticFingerprint"):
        parse_changeset(payload)


def test_rejects_change_set_id_mismatch():
    payload = sample_changeset()
    payload["changeSetId"] = "0" * 24
    with pytest.raises(ChangeSetError, match="changeSetId"):
        parse_changeset(payload)


def test_rejects_invalid_sheet_creates_entries():
    base = sample_changeset()
    valid = {"sheet": "new_options", "family": "options",
             "headersFrom": "stingray_options"}
    cases = []
    p = copy.deepcopy(base)
    p["sheetCreates"] = [dict(valid, extra=1)]
    cases.append(_resign(p))
    p = copy.deepcopy(base)
    entry = dict(valid)
    del entry["headersFrom"]
    p["sheetCreates"] = [entry]
    cases.append(_resign(p))
    p = copy.deepcopy(base)
    p["sheetCreates"] = [dict(valid, sheet=7)]
    cases.append(_resign(p))
    p = copy.deepcopy(base)
    p["sheetCreates"] = [dict(valid, family="not_a_family")]
    cases.append(_resign(p))
    for payload in cases:
        with pytest.raises(ChangeSetError, match="sheetCreates"):
            parse_changeset(payload)


# ── Conversion: Step 4 rules ──────────────────────────────────────────

def test_sheet_creates_convert_first_and_allow_adds_to_created_sheet():
    payload = sample_changeset()
    payload["sheetCreates"] = [{
        "sheet": "new_options",
        "family": "options",
        "headersFrom": "stingray_options",
    }]
    payload["rowChanges"].append({
        "action": "add",
        "sheet": "new_options",
        "family": "options",
        "key": {"option_id": "opt_new"},
        "fields": {"price": {"before": None, "after": 5}},
        "provenance": [{"kind": "editor", "id": "row:new_options:opt_new"}],
    })
    parsed = parse_changeset(_resign(payload))
    batch = changeset_to_editor_batch(parsed, _extract())
    assert batch["items"][0] == {
        "action": "create_sheet",
        "sheet": "new_options",
        "family": "options",
        "headersFrom": "stingray_options",
    }
    # Row changes convert in their given (immutable) changeset order; the
    # update from sample_changeset precedes the appended add.
    assert batch["items"][1] == {
        "action": "update",
        "sheet": "stingray_options",
        "key": {"option_id": "opt_1"},
        "row": {"price": 200},
    }
    assert batch["items"][2] == {
        "action": "add",
        "sheet": "new_options",
        "key": {"option_id": "opt_new"},
        "row": {"price": 5},
    }


def test_delete_emits_key_only_and_verifies_before_values():
    parsed = parse_changeset(_delete_payload())
    batch = changeset_to_editor_batch(parsed, _extract())
    assert batch["items"] == [{
        "action": "delete",
        "sheet": "stingray_options",
        "key": {"option_id": "opt_1"},
    }]
    extract = _extract()
    extract["sheets"]["stingray_options"]["rows"][0]["price"] = 101
    with pytest.raises(ChangeSetError, match="before value"):
        changeset_to_editor_batch(parsed, extract)


def test_add_requires_absent_key_and_emits_full_after_values():
    parsed = parse_changeset(_add_payload())
    batch = changeset_to_editor_batch(parsed, _extract())
    assert batch["items"] == [{
        "action": "add",
        "sheet": "stingray_options",
        "key": {"option_id": "opt_2"},
        "row": {"price": 300, "label": "New"},
    }]
    duplicate = parse_changeset(_add_payload(key_option_id="opt_1"))
    with pytest.raises(ChangeSetError, match="already exists"):
        changeset_to_editor_batch(duplicate, _extract())


def test_update_and_delete_require_existing_sheet_and_row():
    parsed = parse_changeset(sample_changeset())
    with pytest.raises(ChangeSetError, match="missing sheet"):
        changeset_to_editor_batch(parsed, {"sheets": {}})
    extract = _extract()
    extract["sheets"]["stingray_options"]["rows"] = []
    with pytest.raises(ChangeSetError, match="row not found"):
        changeset_to_editor_batch(parsed, extract)
    parsed_delete = parse_changeset(_delete_payload())
    with pytest.raises(ChangeSetError, match="missing sheet"):
        changeset_to_editor_batch(parsed_delete, {"sheets": {}})
    with pytest.raises(ChangeSetError, match="row not found"):
        changeset_to_editor_batch(parsed_delete, extract)


def test_noops_never_produce_items():
    payload = sample_changeset()
    payload["rowChanges"] = []
    payload["noops"] = [{
        "sheet": "stingray_options",
        "key": {"option_id": "opt_1"},
        "reason": "unchanged",
    }]
    parsed = parse_changeset(_resign(payload))
    batch = changeset_to_editor_batch(parsed, _extract())
    assert batch["items"] == []


def test_batch_carries_workbook_freshness_fields():
    parsed = parse_changeset(sample_changeset())
    batch = changeset_to_editor_batch(parsed, _extract())
    assert batch["workbookMtimeNs"] == "123"
    assert batch["workbookSha256"] == "a" * 64


def test_conversion_does_not_alias_parsed_changeset():
    parsed = parse_changeset(sample_changeset())
    batch = changeset_to_editor_batch(parsed, _extract())
    batch["items"][0]["key"]["option_id"] = "mutated"
    batch["items"][0]["row"]["price"] = -1
    assert parsed["rowChanges"][0]["key"] == {"option_id": "opt_1"}
    assert parsed["rowChanges"][0]["fields"]["price"]["after"] == 200


def test_before_value_comparison_tolerates_float_int_equivalence():
    parsed = parse_changeset(sample_changeset())
    extract = _extract()
    extract["sheets"]["stingray_options"]["rows"][0]["price"] = 100.0
    batch = changeset_to_editor_batch(parsed, extract)
    assert batch["items"][0]["row"] == {"price": 200}


def test_before_value_comparison_rejects_bool_int_equivalence():
    payload = sample_changeset()
    payload["rowChanges"][0]["fields"] = {
        "selectable": {"before": True, "after": False},
    }
    parsed = parse_changeset(_resign(payload))
    extract = {"sheets": {"stingray_options": {
        "headers": ["option_id", "selectable"],
        "rows": [{"option_id": "opt_1", "selectable": 1}],
    }}}
    with pytest.raises(ChangeSetError, match="before value"):
        changeset_to_editor_batch(parsed, extract)
