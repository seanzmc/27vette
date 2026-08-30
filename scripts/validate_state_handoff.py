#!/usr/bin/env python3
"""Validate the repo-local operational handoff in fable5loop/STATE.md."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = "fable5loop/STATE.md"
ARCHIVE_FILE = "fable5loop/STATE-archive.md"
CANONICAL_COMMAND = ".venv/bin/python scripts/validate_state_handoff.py"
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?\b")

REQUIRED_SECTIONS = (
    "Memory entry contract",
    "Current handoff",
    "Verified facts",
    "General rules",
    "Open failures",
    "Lessons learned",
    "Last session",
)
HANDOFF_REQUIRED_FIELDS = (
    "Updated",
    "Owning specification",
    "Active workflow",
    "Branch/commit",
    "Last completed",
    "Current status",
    "Validation",
    "Next action",
    "Blockers or closeout gaps",
    "Protected boundaries",
)
EVIDENCE_SECTIONS = ("Verified facts", "General rules", "Open failures", "Lessons learned")
MAX_LAST_SESSION_ENTRIES = 5
MAX_STATE_BYTES = 40_000

CATALOG_FILE = "tests/validation_catalog.json"
# STATE.md quotes catalog inventory counts as verified facts. They go stale
# silently: both files stay individually valid while the claim they share
# becomes false. Each noun below is matched inside any STATE.md sentence that
# cites the catalog, then checked against the catalog itself.
CATALOG_COUNT_NOUNS = {
    "gates": "gates",
    "suites": "suites",
    "acceptance-lock records": "acceptance_locks",
    "coverage-ledger entries": "coverage_ledger",
    "stale assertions": "stale_assertions",
    "findings": "new_findings",
    "expensive setups": "expensive_setups",
}
CATALOG_CLAIM_RE = re.compile(
    r"(\d+)\s+(" + "|".join(re.escape(n) for n in CATALOG_COUNT_NOUNS) + r")\b"
)


def _section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() in {f"## {heading}", f"# {heading}"}:
            start = index + 1
            break
    if start is None:
        return []
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("#"):
            end = index
            break
    return lines[start:end]


def _bullet_texts(text: str, heading: str) -> list[str]:
    return [line.strip()[2:].strip() for line in _section_lines(text, heading) if line.strip().startswith("- ")]


def _validate_command_surface(root: Path, issues: list[str]) -> None:
    readme_path = root / "README.md"
    if not readme_path.is_file():
        issues.append("missing README.md")
    elif CANONICAL_COMMAND not in readme_path.read_text(encoding="utf-8"):
        issues.append(f"README.md missing canonical validator command: {CANONICAL_COMMAND}")


def _validate_state(root: Path, issues: list[str]) -> None:
    state_path = root / STATE_FILE
    if not state_path.is_file():
        issues.append(f"missing state file: {STATE_FILE}")
        return

    state_text = state_path.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in state_text:
            issues.append(f"STATE.md missing section: {section}")

    handoff_bullets = _bullet_texts(state_text, "Current handoff")
    for field in HANDOFF_REQUIRED_FIELDS:
        prefix = f"**{field}:**"
        matches = [bullet for bullet in handoff_bullets if bullet.startswith(prefix)]
        if len(matches) != 1:
            issues.append(f"STATE.md Current handoff must contain exactly one field: {field}")
            continue
        if not matches[0][len(prefix) :].strip():
            issues.append(f"STATE.md Current handoff field is empty: {field}")

    updated_prefix = "**Updated:**"
    updated = next((bullet for bullet in handoff_bullets if bullet.startswith(updated_prefix)), "")
    if updated and not DATE_RE.search(updated[len(updated_prefix) :]):
        issues.append("STATE.md Current handoff Updated field missing ISO date")

    for section in EVIDENCE_SECTIONS:
        for bullet in _bullet_texts(state_text, section):
            if not DATE_RE.search(bullet):
                issues.append(f"STATE.md {section} bullet missing ISO date: {bullet[:120]}")
            if "Evidence:" not in bullet:
                issues.append(f"STATE.md {section} bullet missing Evidence: {bullet[:120]}")

    last_session = "\n".join(_section_lines(state_text, "Last session"))
    entries = [block for block in last_session.split("\n\n") if DATE_RE.match(block.strip())]
    if len(entries) > MAX_LAST_SESSION_ENTRIES:
        issues.append(
            f"STATE.md Last session holds {len(entries)} entries; keep at most "
            f"{MAX_LAST_SESSION_ENTRIES} and move the rest to {ARCHIVE_FILE}"
        )

    size = len(state_text.encode("utf-8"))
    if size > MAX_STATE_BYTES:
        issues.append(
            f"STATE.md is {size} bytes; keep it under {MAX_STATE_BYTES} by moving retired detail to {ARCHIVE_FILE}"
        )

    if not (root / ARCHIVE_FILE).is_file():
        issues.append(f"missing archive file: {ARCHIVE_FILE}")

    _validate_catalog_counts(root, state_text, issues)


def _validate_catalog_counts(root: Path, state_text: str, issues: list[str]) -> None:
    """Any inventory count STATE.md attributes to the catalog must still hold."""

    catalog_path = root / CATALOG_FILE
    if not catalog_path.is_file():
        issues.append(f"missing catalog file: {CATALOG_FILE}")
        return
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"{CATALOG_FILE} is not valid JSON: {exc}")
        return

    for sentence in re.split(r"(?<=[.;])\s+", state_text):
        if CATALOG_FILE not in sentence:
            continue
        for claimed, noun in CATALOG_CLAIM_RE.findall(sentence):
            key = CATALOG_COUNT_NOUNS[noun]
            actual = len(catalog.get(key, ()))
            if int(claimed) != actual:
                issues.append(
                    f"STATE.md claims {claimed} {noun} in {CATALOG_FILE}; it holds "
                    f"{actual}. Update the claim or move it to {ARCHIVE_FILE}"
                )


def validate(root: Path = ROOT) -> list[str]:
    """Return structural issues for the operational handoff."""

    issues: list[str] = []
    _validate_command_surface(root, issues)
    _validate_state(root, issues)
    return issues


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    issues = validate(root)
    if issues:
        print("State handoff validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("State handoff validation passed: required sections, handoff fields, dated evidence, and size budget are in order.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
