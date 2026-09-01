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


def check_closed_scenarios_belong_to_closed_checkpoints(lines: list[str]) -> None:
    """§10 `— closed <date>` labels: only on scenarios whose checkpoint is
    closed, and then on every scenario of that exit gate, not a subset."""
    bodies, closed = checkpoint_bodies(lines), closed_checkpoints(lines)
    closed_scenarios = {
        sid for sid, line in scenario_definitions(lines).items()
        if re.search(r"— closed \d{4}-\d{2}-\d{2}", line)
    }
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
    unclassified role is an AssertionError, never a silent omission.
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
    return matrix


# Roles the registry routes to several sheets but schema_validation does not
# header-compare. Both were verified to have identical headers across their live
# sheets on 2026-09-01 (2 color-override sheets, 6 variant-override sheets), so
# this is a latent gap, not a live defect. Closing it changes generator code and
# is out of scope here; the cell is classified rather than left blank.
KNOWN_UNCHECKED_HEADER_ROLES = frozenset({"color_overrides_sheet", "variant_option_overrides_sheet"})


def check_family_matrix_is_fully_classified(matrix: dict[str, dict[str, str]]) -> None:
    unchecked = {
        row["source_role"] for row in matrix.values() if row.get("header_parity") == "unchecked_known_gap"
    }
    assert unchecked == KNOWN_UNCHECKED_HEADER_ROLES, (
        "header-parity coverage changed; reclassify these roles deliberately: "
        f"{sorted(unchecked ^ KNOWN_UNCHECKED_HEADER_ROLES)}"
    )
    assert len(matrix) == len(registry.EDITOR_SHEET_META) + len(registry.READONLY_SHEET_META)


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
    # §9: header parity silently widened or narrowed must be reclassified.
    with pytest.raises(AssertionError):
        check_family_matrix_is_fully_classified(
            family_surface_matrix(header_match_roles=tuple(registry.SOURCE_ROLE_FAMILIES))
        )
