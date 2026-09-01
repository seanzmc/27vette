#!/usr/bin/env python3
"""Tests for the operational handoff validator."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_state_handoff.py"
SPEC = importlib.util.spec_from_file_location("validate_state_handoff", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
validate = VALIDATOR.validate


def copy_scaffold(tmp_path: Path) -> Path:
    """Copy just enough repo structure for validator mutation tests."""

    (tmp_path / "fable5loop").mkdir()
    for name in ("STATE.md", "STATE-archive.md"):
        shutil.copy2(ROOT / "fable5loop" / name, tmp_path / "fable5loop" / name)
    shutil.copy2(ROOT / "README.md", tmp_path / "README.md")
    (tmp_path / "tests").mkdir()
    shutil.copy2(ROOT / "tests" / "validation_catalog.json", tmp_path / "tests" / "validation_catalog.json")
    return tmp_path


def state_path(tmp_path: Path) -> Path:
    return tmp_path / "fable5loop" / "STATE.md"


def test_repository_state_handoff_passes() -> None:
    assert validate(ROOT) == []


def test_validator_rejects_missing_section(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    state.write_text(state.read_text(encoding="utf-8").replace("## Open failures", "## Retired failures"), encoding="utf-8")
    issues = validate(tmp_path)
    assert any("missing section: Open failures" in issue for issue in issues)


def test_validator_rejects_missing_handoff_field(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    state.write_text(state.read_text(encoding="utf-8").replace("- **Next action:**", "- **Follow-up:**"), encoding="utf-8")
    issues = validate(tmp_path)
    assert any("exactly one field: Next action" in issue for issue in issues)


def test_validator_rejects_empty_handoff_field(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    start = text.index("- **Next action:**")
    end = text.index("\n", start)
    state.write_text(text[:start] + "- **Next action:**" + text[end:], encoding="utf-8")
    issues = validate(tmp_path)
    assert any("field is empty: Next action" in issue for issue in issues)


def test_validator_rejects_undated_updated_field(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    start = text.index("- **Updated:**")
    end = text.index("\n", start)
    state.write_text(text[:start] + "- **Updated:** today" + text[end:], encoding="utf-8")
    issues = validate(tmp_path)
    assert any("Updated field missing ISO date" in issue for issue in issues)


def test_validator_rejects_memory_bullet_without_evidence(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    marker = "\n## General rules\n"
    insert = text.index(marker) + len(marker)
    state.write_text(text[:insert] + "\n- 2026-08-26: An undated-source claim with no proof.\n", encoding="utf-8")
    issues = validate(tmp_path)
    assert any("General rules bullet missing Evidence" in issue for issue in issues)


def test_validator_rejects_memory_bullet_without_date(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    marker = "\n## General rules\n"
    insert = text.index(marker) + len(marker)
    state.write_text(text[:insert] + "\n- A rule with no date. Evidence: `README.md`.\n", encoding="utf-8")
    issues = validate(tmp_path)
    assert any("General rules bullet missing ISO date" in issue for issue in issues)


def test_validator_rejects_overlong_last_session(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    marker = "\n## Last session\n"
    insert = text.index(marker) + len(marker)
    extra = "".join(f"\n2026-08-2{index} (filler): entry.\n" for index in range(3))
    state.write_text(text[:insert] + extra + text[insert:], encoding="utf-8")
    issues = validate(tmp_path)
    assert any("Last session holds" in issue for issue in issues)


def test_validator_rejects_oversized_state_file(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    padding = "\n<!-- " + ("x" * VALIDATOR.MAX_STATE_BYTES) + " -->\n"
    state.write_text(state.read_text(encoding="utf-8") + padding, encoding="utf-8")
    issues = validate(tmp_path)
    assert any("keep it under" in issue for issue in issues)


def test_validator_rejects_missing_archive(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    (tmp_path / "fable5loop" / "STATE-archive.md").unlink()
    issues = validate(tmp_path)
    assert any("missing archive file" in issue for issue in issues)


def test_validator_rejects_readme_without_canonical_command(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(VALIDATOR.CANONICAL_COMMAND, "python scripts/validate_state_handoff.py"),
        encoding="utf-8",
    )
    issues = validate(tmp_path)
    assert any("missing canonical validator command" in issue for issue in issues)


def test_validator_rejects_stale_catalog_count(tmp_path: Path) -> None:
    """A count STATE.md attributes to the catalog must track the catalog.

    Both files stay individually valid when this drifts, so nothing else in
    the suite can see it. The 2026-08-17 entry sat 16 gates stale until this
    check was added.
    """

    copy_scaffold(tmp_path)
    state = state_path(tmp_path)
    text = state.read_text(encoding="utf-8")
    # Anchor on the live count so an additive catalog gate does not break the
    # seed; the validator itself is what must notice a stale number.
    import json

    live = len(json.loads((ROOT / "tests" / "validation_catalog.json").read_text())["gates"])
    anchor = f"holds {live} gates"
    assert anchor in text
    state.write_text(text.replace(anchor, "holds 59 gates"), encoding="utf-8")
    issues = validate(tmp_path)
    assert any("claims 59 gates" in issue for issue in issues), issues


def test_validator_accepts_catalog_counts_that_match(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    assert not [i for i in validate(tmp_path) if "validation_catalog.json" in i]


def test_validator_rejects_missing_catalog(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    (tmp_path / "tests" / "validation_catalog.json").unlink()
    issues = validate(tmp_path)
    assert any("missing catalog file" in issue for issue in issues), issues
