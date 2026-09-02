"""Executable form of the prose-only invariants in `workbook-manager/audit-spec.md`.

Until this file existed, each rule below was enforced only by an implementer
remembering to check it at closeout. Every check is a pure function over the
spec/audit text or over the live registry and Manager catalog objects, so the
mutation canary at the bottom can prove each one fails on a seeded violation
without touching a tracked file. Nothing here reads the workbook, a projection,
or a generated artifact, and nothing writes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "workbook-manager" / "audit-spec.md"
AUDIT_PATH = ROOT / "workbook-manager" / "wbookMgrAuditRpt.md"
CATALOG_PATH = ROOT / "tests" / "validation_catalog.json"
BACKEND = ROOT / "workbook-manager" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import catalog as manager_catalog  # noqa: E402
from corvette_form_generator import model_configs, runtime_metadata, schema_validation  # noqa: E402
from corvette_form_generator.workbook_domain import registry  # noqa: E402

LEDGER_ID_RE = re.compile(r"^- \[( |x)\] \*\*(P[0-9]+\.[0-9]+) / ")
CHECKPOINT_HEADING_RE = re.compile(r"^### Checkpoint ([0-9][A-Z]) — ")
INLINE_CLOSED_RE = re.compile(r"^\*\*Closed (\d{4}-\d{2}-\d{2}) — implementation `([0-9a-f]{7,})`\.\*\*")
SCENARIO_DEF_RE = re.compile(r"^- \*\*([A-Z][A-Z-]*?-\d{2})(?: — [^*]*)?:\*\* ")
FINDING_RE = re.compile(r"^### (WM-\d{3}) — ", re.M)
# `HIST-01–04`, `P2.5–P2.7`, `APPLY-ERR-01–03`; the dash is the spec's en dash.
RANGE_RE = re.compile(r"([A-Z][A-Z-]*?)-(\d{2})–(\d{2})")
ITEM_RANGE_RE = re.compile(r"(P\d+)\.(\d+)–P\d+\.(\d+)")
PR_RE = re.compile(r"\bPR #\d+\b")
RESIDUAL_NONE_RE = re.compile(r"Residual risk:\s*none\s*implied", re.I)
# Explicit deferral vocabulary. Preserved-behavior prose such as "full reversion
# still coalesces away" (1C, which satisfies DRAFT-02) is not a deferral.
CARRIED_LIMITATION_RE = re.compile(
    r"\bknown (?:gap|limitation|defect)\b"
    r"|\bnot (?:yet )?(?:implemented|fixed|addressed|done) here\b"
    r"|\bcarried forward\b"
    r"|\bremains? (?:open|unfixed|unresolved)\b"
    r"|\bdeferred to\b"
    r"|\bneeds its own (?:pass|checkpoint|fix)\b",
    re.I,
)
DELIVERY_STATES = {
    "merged": re.compile(r"merged to `main` as `[0-9a-f]{7,}`"),
    "ci_passed": re.compile(r"CI and Codex finding\s+disposition passed"),
    "ci_pending": re.compile(r"(?:CI|disposition)[^.]{0,80}\bpending\b|\bpending\b[^.]{0,40}\bCI\b"),
}


@pytest.fixture(scope="module")
def spec_lines() -> list[str]:
    return SPEC_PATH.read_text(encoding="utf-8").splitlines()


@pytest.fixture(scope="module")
def audit_text() -> str:
    return AUDIT_PATH.read_text(encoding="utf-8")


# --- spec parsing --------------------------------------------------------------


def _section(lines: list[str], heading_prefix: str) -> tuple[int, int]:
    """[start, end) line indexes of the `## N.` section."""
    start = next(i for i, line in enumerate(lines) if line.startswith(heading_prefix))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return start, end


def ledger_items(lines: list[str]) -> dict[str, bool]:
    """Ordered `{priority_id: checked}` from §3; a duplicate id raises."""
    start, end = _section(lines, "## 3. ")
    items: dict[str, bool] = {}
    for line in lines[start:end]:
        match = LEDGER_ID_RE.match(line)
        if match:
            assert match.group(2) not in items, f"duplicate ledger id {match.group(2)}"
            items[match.group(2)] = match.group(1) == "x"
    return items


def audit_backlog_ids(audit_text: str) -> list[str]:
    """`P1.1 … P3.8` from the audit report §9 numbered bullets."""
    section = audit_text[audit_text.index("## 9. Prioritized remediation backlog"):]
    section = section[: section.index("## Direct answers")]
    ids: list[str] = []
    priority = None
    for line in section.splitlines():
        heading = re.match(r"^### (P\d)", line)
        if heading:
            priority = heading.group(1)
            continue
        numbered = re.match(r"^(\d+)\. ", line)
        if numbered and priority:
            ids.append(f"{priority}.{numbered.group(1)}")
    return ids


def expand_ranges(text: str) -> set[str]:
    """Every scenario/priority id a cell names, with ranges expanded."""
    found: set[str] = set()
    for prefix, lo, hi in RANGE_RE.findall(text):
        found.update(f"{prefix}-{n:02d}" for n in range(int(lo), int(hi) + 1))
    for prefix, lo, hi in ITEM_RANGE_RE.findall(text):
        found.update(f"{prefix}.{n}" for n in range(int(lo), int(hi) + 1))
    stripped = RANGE_RE.sub(" ", ITEM_RANGE_RE.sub(" ", text))
    found.update(re.findall(r"\b[A-Z][A-Z-]*?-\d{2}\b", stripped))
    found.update(re.findall(r"\bP\d+\.\d+\b", stripped))
    return found


def scenario_definitions(lines: list[str]) -> dict[str, str]:
    start, end = _section(lines, "## 10. ")
    defs: dict[str, str] = {}
    for line in lines[start:end]:
        match = SCENARIO_DEF_RE.match(line)
        if match:
            assert match.group(1) not in defs, f"duplicate scenario {match.group(1)}"
            defs[match.group(1)] = line
    return defs


def traceability_rows(lines: list[str]) -> list[dict[str, str]]:
    start, end = _section(lines, "## 4. ")
    rows = []
    for line in lines[start:end]:
        if line.startswith("| WM-"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            rows.append(dict(zip(("finding", "items", "checkpoint", "scenarios"), cells)))
    return rows


def checkpoint_bodies(lines: list[str]) -> dict[str, list[str]]:
    bodies: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line.startswith("## "):
            current = None
        match = CHECKPOINT_HEADING_RE.match(line)
        if match:
            current = match.group(1)
            bodies[current] = []
            continue
        if current:
            bodies[current].append(line)
    return bodies


def closed_checkpoints(lines: list[str]) -> set[str]:
    return {
        name for name, body in checkpoint_bodies(lines).items()
        if any(INLINE_CLOSED_RE.match(line) for line in body)
    }


def checkpoint_items(body: list[str]) -> set[str]:
    objective = next(line for line in body if line.startswith("Objective:"))
    return {token for token in expand_ranges(objective) if token.startswith("P")}


def completion_records(lines: list[str]) -> dict[str, str]:
    """`{checkpoint: record text}`: the inline closure text from §§6–8 plus the
    §14 dated bullet, so the checks hold wherever a checkpoint keeps evidence."""
    records: dict[str, list[str]] = {}
    for name, body in checkpoint_bodies(lines).items():
        closed_at = next((i for i, line in enumerate(body) if INLINE_CLOSED_RE.match(line)), None)
        if closed_at is not None:
            records.setdefault(name, []).extend(body[closed_at:])
    start, end = _section(lines, "## 14. ")
    current = None
    for line in lines[start:end]:
        match = re.match(r"^- \*\*\d{4}-\d{2}-\d{2} — Checkpoint ([0-9][A-Z]) / ", line)
        if match:
            current = match.group(1)
            records.setdefault(current, []).append(line)
        elif current and line.startswith("  "):
            records[current].append(line)
        else:
            current = None
    return {key: "\n".join(value) for key, value in records.items()}


# --- the checks (pure; each raises AssertionError on violation) ---------------


def check_ledger_equals_audit_backlog(lines: list[str], audit_text: str) -> None:
    """§3: 'preserves all 23 items from audit report §9 … must not be deleted,
    merged away'. Fails on a removed, renumbered, duplicated, or reordered item."""
    assert list(ledger_items(lines)) == audit_backlog_ids(audit_text)
    assert len(ledger_items(lines)) == 23


def check_every_finding_traces_to_items_and_scenarios(lines: list[str], audit_text: str) -> None:
    """§2 condition 2: every WM finding maps to ≥1 ledger item and ≥1 defined
    scenario through the §4 table."""
    findings = FINDING_RE.findall(audit_text)
    assert len(findings) == 11
    rows = {row["finding"]: row for row in traceability_rows(lines)}
    assert set(rows) == set(findings), set(findings) ^ set(rows)
    ledger, scenarios = ledger_items(lines), scenario_definitions(lines)
    for finding, row in rows.items():
        items = {t for t in expand_ranges(row["items"]) if t.startswith("P")}
        assert items and items <= set(ledger), (finding, items - set(ledger))
        named = {t for t in expand_ranges(row["scenarios"]) if "-" in t}
        assert named and named <= set(scenarios), (finding, named - set(scenarios))


def check_items_appear_literally_in_checkpoint_objectives(lines: list[str]) -> None:
    """§4 + §6–8: each §4 row's items appear literally in the objective of the
    checkpoint(s) it names, and every ledger item is owned by some checkpoint."""
    bodies = checkpoint_bodies(lines)
    owned: set[str] = set()
    for row in traceability_rows(lines):
        items = {t for t in expand_ranges(row["items"]) if t.startswith("P")}
        checkpoints = re.findall(r"\b[0-9][A-Z]\b", row["checkpoint"])
        assert checkpoints, row
        covered: set[str] = set()
        for checkpoint in checkpoints:
            assert checkpoint in bodies, f"{row['finding']} names unknown checkpoint {checkpoint}"
            covered |= checkpoint_items(bodies[checkpoint]) & items
        assert covered == items, (row["finding"], items - covered)
        owned |= covered
    assert owned == set(ledger_items(lines)), set(ledger_items(lines)) - owned


def check_checkboxes_match_closures(lines: list[str]) -> None:
    """§12 'mark only evidence-backed ledger items complete': `[x]` iff the
    owning checkpoint carries `**Closed … — implementation <sha>.**`."""
    ledger, closed = ledger_items(lines), closed_checkpoints(lines)
    for name, body in checkpoint_bodies(lines).items():
        for item in checkpoint_items(body):
            assert ledger[item] == (name in closed), (
                f"{item} is {'checked' if ledger[item] else 'unchecked'} but "
                f"Checkpoint {name} is {'closed' if name in closed else 'open'}"
            )


# Exit-gate scenarios currently carrying §10 `— closed <date>` labels (live
# spec, 2026-09-01): the five DRAFT scenarios of closed Checkpoint 1C.
# Checkpoints 1A, 1B, 1D, 1E, 2A, and 2B closed through their §6–8/§14 records
# without per-scenario labels — §10 itself defines no mandatory label — so an
# empty `marked` is legitimate for them. Pinning the labeled set closes the one
# drift the per-row loop below cannot see: removing any or all current labels
# leaves `marked` empty, the loop then asserts nothing, and the check stayed
# green. Now that removal fails here until the pin is deliberately updated
# alongside the spec edit.
EXPECTED_CLOSED_SCENARIOS = frozenset({
    "DRAFT-01", "DRAFT-02", "DRAFT-03", "DRAFT-04", "DRAFT-05",
})


def check_closed_scenarios_belong_to_closed_checkpoints(lines: list[str]) -> None:
    """§10 `— closed <date>` labels: only on scenarios whose checkpoint is
    closed, then on every scenario of that exit gate, not a subset, and never
    silently removed from the labeled set."""
    bodies, closed = checkpoint_bodies(lines), closed_checkpoints(lines)
    closed_scenarios = {
        sid for sid, line in scenario_definitions(lines).items()
        if re.search(r"— closed \d{4}-\d{2}-\d{2}", line)
    }
    assert closed_scenarios == EXPECTED_CLOSED_SCENARIOS, (
        "closed-scenario labels changed; relabel deliberately and update "
        f"EXPECTED_CLOSED_SCENARIOS: {sorted(closed_scenarios ^ EXPECTED_CLOSED_SCENARIOS)}"
    )
    for row in traceability_rows(lines):
        named = {t for t in expand_ranges(row["scenarios"]) if "-" in t}
        for checkpoint in re.findall(r"\b[0-9][A-Z]\b", row["checkpoint"]):
            exit_gate = next(line for line in bodies[checkpoint] if line.startswith("Exit gate:"))
            gate_scenarios = expand_ranges(exit_gate) & named
            marked = gate_scenarios & closed_scenarios
            if marked:
                assert checkpoint in closed, (checkpoint, marked)
                assert marked == gate_scenarios, (checkpoint, gate_scenarios - marked)


def check_residual_risk_is_not_contradicted(lines: list[str]) -> None:
    """§14 'residual risk or "none implied"': a record may not claim none while
    also deferring work ('not fixed here', 'carried forward', 'needs its own pass')."""
    offenders = []
    for checkpoint, record in completion_records(lines).items():
        limitation = CARRIED_LIMITATION_RE.search(record)
        if RESIDUAL_NONE_RE.search(record) and limitation:
            offenders.append((checkpoint, limitation.group(0)))
    assert not offenders, f"'none implied' beside a carried limitation: {offenders}"


# Closed checkpoints whose spec record names no PR. 1A shipped through PR #60
# (`230ed99`, `832d692`) and 2A through PR #69 (`87a2095`, merge `c24cc82`), per
# `gh pr view`; both records omit the PR and 2A has no §14 bullet at all — its
# delivery lives only in `fable5loop/STATE.md`. Adding the PR to either closure
# makes this set shrink, and the assertion below then fails until the entry is
# removed, so the exception cannot outlive the gap it documents.
CLOSED_WITHOUT_PR_RECORD = frozenset({"1A", "2A"})


# §11.2 item 1 (2026-09-01 amendment): a RED is a failing assertion against
# existing code, never an existence failure. This regex is the checkable half of
# that rule — it catches a closure that *cites* an existence failure as its RED.
# It cannot verify that a RED ever ran, that it ran against the unmodified tree,
# or that the assertion it names was the decisive one; those remain review.
EXISTENCE_FAILURE_RE = re.compile(
    r"\b(?:RED|first failed|failures? proved|initial focused .{0,40}?failed)\b[^.]{0,200}?"
    r"(?:`404`|\b404\b|ERR_MODULE_NOT_FOUND|ModuleNotFoundError|ImportError|"
    r"\bmissing (?:\w+ )?(?:endpoint|import|selector|module|symbol)\b|\babsent (?:\w+ )?(?:selector|endpoint|route|import)\b|"
    r"\bundefined (?:symbol|export)\b|is not defined\b|cannot find module\b)",
    re.I | re.S,
)

# Closures written before the rule and left as evidence: 1A (`404`), 1B (absent
# registry selector), 1D (`ERR_MODULE_NOT_FOUND`). Fixing them would be
# retroactive editing of evidence; the set is pinned so the exception cannot grow
# and shrinks (failing the assertion) if a record is rewritten.
RED_EXISTENCE_FAILURE_RECORDS = frozenset({"1A", "1B", "1D"})


def check_red_evidence_is_not_an_existence_failure(lines: list[str]) -> None:
    """§11.2 item 1: no closed checkpoint may cite a 404 / missing import / absent
    selector as its RED proof, except the three pre-rule records pinned above."""
    offenders = {
        checkpoint
        for checkpoint, record in completion_records(lines).items()
        if EXISTENCE_FAILURE_RE.search(record)
    }
    # Checkpoint bodies carry validation prose above the closure line; include it.
    for name, body in checkpoint_bodies(lines).items():
        if name in closed_checkpoints(lines) and EXISTENCE_FAILURE_RE.search("\n".join(body)):
            offenders.add(name)
    assert offenders == RED_EXISTENCE_FAILURE_RECORDS, (
        "closed checkpoints citing an existence failure as RED changed; "
        f"now {sorted(offenders)}, pinned {sorted(RED_EXISTENCE_FAILURE_RECORDS)}. "
        "A new entry violates §11.2 item 1; a removed entry means re-pin."
    )


def check_every_closed_checkpoint_records_delivery(lines: list[str]) -> None:
    """§12/§14: a closed checkpoint names its PR, and any CI/merge wording it
    carries is self-consistent (never 'pending' beside 'passed' or 'merged').
    The exit gate is the acceptance scenarios plus PR delivery; merge is a
    separate authority, so 'CI pending', 'CI passed', and 'merged' are all valid
    closure states — what is invalid is a closure that names no PR."""
    records = completion_records(lines)
    missing_pr = set()
    for checkpoint in sorted(closed_checkpoints(lines)):
        record = records.get(checkpoint, "")
        if not PR_RE.search(record):
            missing_pr.add(checkpoint)
        matched = {name for name, pattern in DELIVERY_STATES.items() if pattern.search(record)}
        assert not ("ci_pending" in matched and matched & {"merged", "ci_passed"}), (
            checkpoint, sorted(matched)
        )
    assert missing_pr == CLOSED_WITHOUT_PR_RECORD, (
        "closed checkpoints with no PR in their record changed; "
        f"now {sorted(missing_pr)}, documented {sorted(CLOSED_WITHOUT_PR_RECORD)}"
    )


def family_surface_matrix(
    *,
    editor_meta=registry.EDITOR_SHEET_META,
    readonly_meta=registry.READONLY_SHEET_META,
    role_families=registry.SOURCE_ROLE_FAMILIES,
    routing=manager_catalog._ROUTING,
    model_collections=manager_catalog.MODEL_COLLECTIONS,
    shared_tables=manager_catalog.SHARED_TABLES,
    structure_tables=manager_catalog.STRUCTURE_TABLES,
    generation_roles=(
        model_configs.REQUIRED_GENERATION_SOURCE_ROLES
        + model_configs.OPTIONAL_GENERATION_SOURCE_ROLES
    ),
    metadata_roles=runtime_metadata._MODEL_CONFIG_SOURCE_ROLES,
    header_match_roles=schema_validation.HEADER_MATCH_ROLES,
) -> dict[str, dict[str, str]]:
    """Classify every registry family and source role on every consuming surface.

    §9: 'Coverage tests enumerate the union of registry families, projected
    families, editable routes, and relevant generated consumers, then classify
    every member.' Every cell gets a positive label; an unroutable family or an
    unclassified role is an AssertionError, never a silent omission. The role
    union is checked in both directions: consumer role lists may not name a
    role SOURCE_ROLE_FAMILIES does not classify.
    """
    matrix: dict[str, dict[str, str]] = {}
    operation_tables = set(model_collections) | set(shared_tables)
    for family in list(editor_meta) + list(readonly_meta):
        row: dict[str, str] = {}
        if family in readonly_meta:
            row["projection"] = "read_only_spec"
            row["manager_surface"] = "shared_read_only" if "form_sections" in shared_tables else "unexposed"
        else:
            assert family in routing, f"registry family {family!r} has no Manager routing"
            table = routing[family][0]
            row["projection"] = f"table:{table}"
            if table in operation_tables and table in structure_tables:
                raise AssertionError(f"{family!r} is routed to both operations and structure")
            if table in operation_tables:
                row["manager_surface"] = "advanced_collection"
            elif table in structure_tables:
                row["manager_surface"] = "structure_index"
            else:
                raise AssertionError(
                    f"registry family {family!r} (table {table!r}) is reachable through "
                    "neither MODEL_COLLECTIONS/SHARED_TABLES nor structure_specs()"
                )
        matrix[family] = row

    role_by_family = {family: role for role, family in role_families.items()}
    for family, row in matrix.items():
        role = role_by_family.get(family)
        if role is None:
            row["source_role"] = "fixed_sheet"
            continue
        row["source_role"] = role
        assert role in generation_roles, f"{role} is a registry role model_configs does not generate from"
        assert role in metadata_roles, f"{role} is a registry role runtime_metadata does not load"
        row["header_parity"] = "checked" if role in header_match_roles else "unchecked_known_gap"

    # The per-family loop above only proves registry roles are covered by the
    # consumers. A consumer list that adds a role SOURCE_ROLE_FAMILIES never
    # classifies sits outside that loop and would pass unexamined, so the
    # union is enforced in this direction too.
    registry_roles = set(role_families)
    for consumer, roles in (
        ("model_configs", generation_roles),
        ("runtime_metadata", metadata_roles),
        ("schema_validation", header_match_roles),
    ):
        unclassified = sorted(set(roles) - registry_roles)
        assert not unclassified, (
            f"{consumer} consumes source role(s) absent from SOURCE_ROLE_FAMILIES; "
            f"classify them in the registry: {unclassified}"
        )
    return matrix


# Roles the registry routes to several sheets but schema_validation does not
# header-compare. Both were verified to have identical headers across their live
# sheets on 2026-09-01 (2 color-override sheets, 6 variant-override sheets), so
# this is a latent gap, not a live defect. Closing it changes generator code and
# is out of scope here; the cell is classified rather than left blank.
KNOWN_UNCHECKED_HEADER_ROLES = frozenset({"color_overrides_sheet", "variant_option_overrides_sheet"})

# Where each registry family is exposed in the Manager today (verified against
# the live matrix 2026-09-01). Moving a family between surfaces is a product
# decision (audit §2, P2.9 PRES-01/05), so it must be made here explicitly
# rather than by editing MODEL_COLLECTIONS / structure_specs() alone.
PINNED_MANAGER_SURFACE = {
    "advanced_collection": frozenset({
        "asset_map", "color_overrides", "default_selection_rules", "exclusive_groups",
        "exclusive_members", "interior_components", "interiors", "model_interior_scope",
        "options", "ovs", "price_rules", "rule_group_members", "rule_groups",
        "rule_mapping", "variant_overrides",
    }),
    "structure_index": frozenset({
        "context_section_master_meta", "model_master", "model_registry_promotion",
        "model_variants", "model_workbook_sources", "order_summary_sections_meta",
        "runtime_steps_meta", "section_presentation_meta", "step_order_summary_map_meta",
        "variant_master",
    }),
    "shared_read_only": frozenset({"sections"}),
}


def check_family_matrix_is_fully_classified(matrix: dict[str, dict[str, str]]) -> None:
    unchecked = {
        row["source_role"] for row in matrix.values() if row.get("header_parity") == "unchecked_known_gap"
    }
    assert unchecked == KNOWN_UNCHECKED_HEADER_ROLES, (
        "header-parity coverage changed; reclassify these roles deliberately: "
        f"{sorted(unchecked ^ KNOWN_UNCHECKED_HEADER_ROLES)}"
    )
    assert len(matrix) == len(registry.EDITOR_SHEET_META) + len(registry.READONLY_SHEET_META)
    live = {
        surface: frozenset(f for f, row in matrix.items() if row["manager_surface"] == surface)
        for surface in PINNED_MANAGER_SURFACE
    }
    drift = {
        surface: sorted(live[surface] ^ PINNED_MANAGER_SURFACE[surface])
        for surface in PINNED_MANAGER_SURFACE
        if live[surface] != PINNED_MANAGER_SURFACE[surface]
    }
    assert not drift, f"family moved between Manager surfaces; re-pin deliberately: {drift}"


# --- preserved-sheet universe pin (Checkpoint 2D precondition) -----------------

# The four sheets Checkpoint 2D (spec §7, "direct management of preserved
# sheets") will register as writable families, and the generator's required
# fixed-sheet list. Neither is registry-derived: `KNOWN_PRESERVED_SHEETS`
# (catalog.py:25-31) is the only thing separating `workbook_preserved_known`
# from `workbook_preserved_unknown` in classify_workbook_sheets (catalog.py:
# 437-441), and `REQUIRED_SHEETS` (schema_validation.py:84-96) is what
# `required_sheet_names()` (catalog.py:478-485) and the importer's
# `missing_sheet` error (importer.py:320-326) key on. 2D moves sheets *out* of
# the first set and *into* the registry; pinning both here makes that move a
# deliberate edit rather than a side effect, and catches a sheet renamed or
# dropped from the generator list before the Manager silently reclassifies it
# as unknown.
PINNED_PRESERVED_SHEETS = frozenset({
    "PriceRef", "context_choice_copy", "rule_phrase_map", "runtime_rule_exceptions",
})
PINNED_REQUIRED_SHEETS = frozenset({
    "model_master", "model_workbook_sources", "model_variants", "model_registry_promotion",
    "variant_master", "section_master", "lt_interiors", "LZ_Interiors",
    "model_interior_scope", "interior_components", "PriceRef",
})


def check_preserved_and_required_sheets_are_pinned(
    *,
    preserved=manager_catalog.KNOWN_PRESERVED_SHEETS,
    required=schema_validation.REQUIRED_SHEETS,
    table_specs=manager_catalog.TABLE_SPECS,
) -> None:
    """2D precondition: the preserved-sheet set and the generator's required-sheet
    list match their pins, and no preserved sheet is *also* already addressed by
    a Manager `TableSpec.sheet` (which would make it both workbook-owned and
    Manager-projected)."""
    assert set(preserved) == PINNED_PRESERVED_SHEETS, (
        "KNOWN_PRESERVED_SHEETS changed; Checkpoint 2D owns that move — re-pin deliberately: "
        f"{sorted(set(preserved) ^ PINNED_PRESERVED_SHEETS)}"
    )
    assert set(required) == PINNED_REQUIRED_SHEETS, (
        "REQUIRED_SHEETS changed; re-pin deliberately: "
        f"{sorted(set(required) ^ PINNED_REQUIRED_SHEETS)}"
    )
    spec_sheets = {sheet for spec in table_specs for sheet in (spec.sheet or ())}
    overlap = spec_sheets & set(preserved)
    assert not overlap, f"preserved sheets already addressed by a Manager TableSpec: {sorted(overlap)}"


# --- tests against the live repository ----------------------------------------


def test_ledger_ids_equal_the_audit_backlog_in_order(spec_lines, audit_text):
    check_ledger_equals_audit_backlog(spec_lines, audit_text)


def test_every_finding_maps_to_a_ledger_item_and_a_scenario(spec_lines, audit_text):
    check_every_finding_traces_to_items_and_scenarios(spec_lines, audit_text)


def test_traceability_items_appear_literally_in_their_checkpoint_objective(spec_lines):
    check_items_appear_literally_in_checkpoint_objectives(spec_lines)


def test_checked_items_have_a_closed_checkpoint_and_vice_versa(spec_lines):
    check_checkboxes_match_closures(spec_lines)


def test_closed_scenarios_belong_to_closed_checkpoints(spec_lines):
    check_closed_scenarios_belong_to_closed_checkpoints(spec_lines)


def test_residual_risk_none_implied_is_not_paired_with_a_named_limitation(spec_lines):
    check_residual_risk_is_not_contradicted(spec_lines)


def test_every_closed_checkpoint_names_its_pr_with_consistent_delivery_state(spec_lines):
    check_every_closed_checkpoint_records_delivery(spec_lines)


def test_every_registry_family_and_role_is_classified_on_every_surface():
    check_family_matrix_is_fully_classified(family_surface_matrix())


def test_preserved_and_required_sheet_universes_are_pinned():
    check_preserved_and_required_sheets_are_pinned()


def test_no_new_closure_cites_an_existence_failure_as_red(spec_lines):
    check_red_evidence_is_not_an_existence_failure(spec_lines)


def test_this_gate_is_cataloged_as_read_only():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    gate = next(g for g in catalog["gates"] if Path(__file__).name in " ".join(g["test_files"]))
    assert gate["isolation"] == "read_only" and gate["writes"] == [] and gate["generates"] is False


# --- mutation canary: every check fails on a seeded violation ------------------


def test_checks_fail_on_seeded_violations(spec_lines, audit_text):
    text = "\n".join(spec_lines)

    def seeded(old: str, new: str, count: int = 1) -> list[str]:
        assert old in text, f"seed anchor missing: {old!r}"
        return text.replace(old, new, count).splitlines()

    # §3: drop one ledger item.
    with pytest.raises(AssertionError):
        check_ledger_equals_audit_backlog(
            [l for l in spec_lines if not l.startswith("- [ ] **P3.8 / ")], audit_text
        )
    # §4: point WM-010 at a scenario family §10 never defines.
    with pytest.raises(AssertionError):
        check_every_finding_traces_to_items_and_scenarios(
            seeded("| WM-010 | P2.8 | 2C | EFFECTIVE-01–04 |", "| WM-010 | P2.8 | 2C | GHOST-01–04 |"),
            audit_text,
        )
    # §4 ↔ objective: retarget WM-010 to a checkpoint whose objective omits P2.8.
    with pytest.raises(AssertionError):
        check_items_appear_literally_in_checkpoint_objectives(
            seeded("| WM-010 | P2.8 | 2C |", "| WM-010 | P2.8 | 2D |")
        )
    # §12: tick P2.8 while Checkpoint 2C stays open.
    with pytest.raises(AssertionError):
        check_checkboxes_match_closures(seeded("- [ ] **P2.8 / WM-010", "- [x] **P2.8 / WM-010"))
    # §10: mark one scenario of an open checkpoint closed.
    with pytest.raises(AssertionError):
        check_closed_scenarios_belong_to_closed_checkpoints(
            seeded("- **EFFECTIVE-01:**", "- **EFFECTIVE-01 — closed 2026-09-01:**")
        )
    # §10: strip every closure label from Checkpoint 1C's scenarios. `marked`
    # is then empty and the per-row loop asserts nothing, so the pinned labeled
    # set is what must go red here.
    with pytest.raises(AssertionError):
        check_closed_scenarios_belong_to_closed_checkpoints(
            seeded(" — closed 2026-08-31", "", count=5)
        )
    # §14: defer work in the same record that claims no residual risk.
    with pytest.raises(AssertionError):
        check_residual_risk_is_not_contradicted(
            seeded(
                "Residual risk: none implied. Checkpoint 1C was",
                "Residual risk: none implied. The stale-transition race is not fixed here. Checkpoint 1C was",
            )
        )
    # §14: report CI pending in a record that also reports the merge.
    with pytest.raises(AssertionError):
        check_every_closed_checkpoint_records_delivery(
            seeded("PR #65 merged to `main` as `d0ad7cc`", "PR #65 (CI pending) merged to `main` as `d0ad7cc`")
        )
    # §14: a closed checkpoint with no PR anywhere in its record (2B loses both
    # mentions), and the documented 1A exception being closed without removal.
    with pytest.raises(AssertionError):
        check_every_closed_checkpoint_records_delivery(seeded("PR #70", "PR-70", count=2))
    with pytest.raises(AssertionError):
        check_every_closed_checkpoint_records_delivery(
            seeded("**Closed 2026-08-29 — implementation `230ed99`.**",
                   "**Closed 2026-08-29 — implementation `230ed99`.** PR #60.")
        )
    # §9: shrink the Advanced-collection universe by one registry family.
    with pytest.raises(AssertionError):
        family_surface_matrix(
            model_collections=tuple(t for t in manager_catalog.MODEL_COLLECTIONS if t != "pricing")
        )
    # §9: a generator role list that drops a registry role.
    with pytest.raises(AssertionError):
        family_surface_matrix(
            generation_roles=tuple(
                r for r in model_configs.REQUIRED_GENERATION_SOURCE_ROLES if r != "status_sheet"
            )
        )
    # §9: consumer-only drift — a consumer list gains a role the registry never
    # classified. Each of the three lists must fail the reverse union.
    with pytest.raises(AssertionError):
        family_surface_matrix(
            generation_roles=(
                model_configs.REQUIRED_GENERATION_SOURCE_ROLES
                + model_configs.OPTIONAL_GENERATION_SOURCE_ROLES
                + ("unclassified_consumer_sheet",)
            )
        )
    with pytest.raises(AssertionError):
        family_surface_matrix(
            metadata_roles=(
                *runtime_metadata._MODEL_CONFIG_SOURCE_ROLES,
                "unclassified_consumer_sheet",
            )
        )
    with pytest.raises(AssertionError):
        family_surface_matrix(
            header_match_roles=(
                *schema_validation.HEADER_MATCH_ROLES,
                "unclassified_consumer_sheet",
            )
        )
    # §9: header parity silently widened or narrowed must be reclassified.
    with pytest.raises(AssertionError):
        check_family_matrix_is_fully_classified(
            family_surface_matrix(header_match_roles=tuple(registry.SOURCE_ROLE_FAMILIES))
        )
    # §9 / P2.9: a family silently moved from Advanced to the structure index
    # (dropped from MODEL_COLLECTIONS and given a structure spec) must re-pin.
    with pytest.raises(AssertionError, match="moved between Manager surfaces"):
        check_family_matrix_is_fully_classified(
            family_surface_matrix(
                model_collections=tuple(t for t in manager_catalog.MODEL_COLLECTIONS if t != "pricing"),
                structure_tables=tuple(manager_catalog.STRUCTURE_TABLES) + ("pricing",),
            )
        )
    # 2D precondition: a preserved sheet dropped (as 2D will do) or a required
    # sheet renamed must re-pin; a preserved sheet that gains a TableSpec is a
    # dual-ownership error.
    with pytest.raises(AssertionError, match="KNOWN_PRESERVED_SHEETS changed"):
        check_preserved_and_required_sheets_are_pinned(
            preserved=tuple(s for s in manager_catalog.KNOWN_PRESERVED_SHEETS if s != "PriceRef")
        )
    with pytest.raises(AssertionError, match="REQUIRED_SHEETS changed"):
        check_preserved_and_required_sheets_are_pinned(
            required=tuple(s if s != "LZ_Interiors" else "lz_interiors" for s in schema_validation.REQUIRED_SHEETS)
        )
    with pytest.raises(AssertionError, match="already addressed by a Manager TableSpec"):
        spec = manager_catalog.TABLE_SPECS[0]
        check_preserved_and_required_sheets_are_pinned(
            table_specs=(*manager_catalog.TABLE_SPECS, spec.__class__(**{**spec.__dict__, "sheet": ("PriceRef",)}))
        )
    # §11.2 item 1: a new closure citing an existence failure as RED (2B gains one)
    # fails; a pre-rule record rewritten to remove its 404 also fails (re-pin).
    with pytest.raises(AssertionError, match="citing an existence failure as RED changed"):
        check_red_evidence_is_not_an_existence_failure(
            seeded("**Closed 2026-09-01 — implementation `845c105`.**",
                   "**Closed 2026-09-01 — implementation `845c105`.** RED tests first failed with `404` on the absent endpoint.")
        )
    with pytest.raises(AssertionError, match="citing an existence failure as RED changed"):
        check_red_evidence_is_not_an_existence_failure(
            seeded("focused RED failures proved the missing endpoint (`404`), missing",
                   "focused RED failures proved the wrong status list, missing")
        )
