#!/usr/bin/env python3
"""Tests for the Fable 5 compounding-loop scaffold."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_fable5_loop.py"
SPEC = importlib.util.spec_from_file_location("validate_fable5_loop", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
validate = VALIDATOR.validate


def copy_scaffold(tmp_path: Path) -> Path:
    """Copy just enough repo structure for validator mutation tests."""

    shutil.copytree(ROOT / "fable5loop", tmp_path / "fable5loop")
    (tmp_path / ".claude" / "skills" / "27vette-fable5-compounding").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    shutil.copy2(ROOT / "README.md", tmp_path / "README.md")
    shutil.copy2(ROOT / ".claude" / "CLAUDE.md", tmp_path / ".claude" / "CLAUDE.md")
    shutil.copy2(
        ROOT / ".claude" / "skills" / "27vette-fable5-compounding" / "SKILL.md",
        tmp_path / ".claude" / "skills" / "27vette-fable5-compounding" / "SKILL.md",
    )
    shutil.copy2(ROOT / "scripts" / "validate_fable5_loop.py", tmp_path / "scripts" / "validate_fable5_loop.py")
    shutil.copy2(ROOT / "tests" / "test_fable5_loop_contract.py", tmp_path / "tests" / "test_fable5_loop_contract.py")
    return tmp_path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_repository_fable5_loop_contract_passes() -> None:
    assert validate(ROOT) == []


def test_validator_rejects_missing_compound_stack_layer(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    dst = tmp_path / "fable5loop"

    contract_path = dst / "fable5-loop-contract.json"
    contract = load_json(contract_path)
    contract["compoundStack"] = contract["compoundStack"][:3]
    write_json(contract_path, contract)

    issues = validate(tmp_path)
    assert "expected exactly 4 compound-stack layers, found 3" in issues


def test_validator_rejects_direct_script_only_documentation(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    readme = tmp_path / "fable5loop" / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nRun `scripts/validate_fable5_loop.py`.\n",
        encoding="utf-8",
    )

    issues = validate(tmp_path)
    assert any("direct validator invocation" in issue for issue in issues)


def test_validator_rejects_missing_claude_project_memory(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    (tmp_path / ".claude" / "CLAUDE.md").unlink()

    issues = validate(tmp_path)
    assert any("missing Claude project memory file" in issue for issue in issues)


def test_validator_rejects_stale_claude_skill_wrapper(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    wrapper = tmp_path / ".claude" / "skills" / "27vette-fable5-compounding" / "SKILL.md"
    wrapper.write_text(
        wrapper.read_text(encoding="utf-8").replace("fable5loop/STATE.md", "fable5loop/OLD_STATE.md"),
        encoding="utf-8",
    )

    issues = validate(tmp_path)
    assert any(".claude/skills/27vette-fable5-compounding/SKILL.md missing phrase: fable5loop/STATE.md" in issue for issue in issues)


def test_validator_rejects_missing_run_receipt_file(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    (tmp_path / "fable5loop" / "runs" / "2026-07-05-scaffold-hardening-review" / "verifier-report.md").unlink()

    issues = validate(tmp_path)
    assert any("missing run receipt artifact" in issue for issue in issues)


def test_validator_rejects_missing_skill_update_evidence(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    run_json = tmp_path / "fable5loop" / "runs" / "2026-07-05-scaffold-hardening-review" / "run.json"
    payload = load_json(run_json)
    payload["skill_update"]["evidence"] = "fable5loop/runs/2026-07-05-scaffold-hardening-review/missing-skill-proof.md"
    write_json(run_json, payload)

    issues = validate(tmp_path)
    assert any("skill_update.evidence path does not exist" in issue for issue in issues)


def test_validator_rejects_state_fact_without_timestamped_evidence(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = tmp_path / "fable5loop" / "STATE.md"
    state_text = state.read_text(encoding="utf-8")
    state.write_text(
        state_text.replace("## Verified facts\n\n", "## Verified facts\n\n- Missing timestamp and evidence.\n"),
        encoding="utf-8",
    )

    issues = validate(tmp_path)
    assert any("STATE.md Verified facts bullet missing ISO date" in issue for issue in issues)
    assert any("STATE.md Verified facts bullet missing Evidence:" in issue for issue in issues)


def test_validator_rejects_stale_last_session_pointer(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    state = tmp_path / "fable5loop" / "STATE.md"
    state.write_text(
        state.read_text(encoding="utf-8").replace(
            "fable5loop/runs/2026-07-05-scaffold-hardening-review",
            "fable5loop/runs/2026-07-04-stale-run",
        ),
        encoding="utf-8",
    )

    issues = validate(tmp_path)
    assert any("STATE.md Last session does not reference latest run folder" in issue for issue in issues)


def test_validator_rejects_run_receipt_without_verifier_verdict(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    verifier = tmp_path / "fable5loop" / "runs" / "2026-07-05-scaffold-hardening-review" / "verifier-report.md"
    verifier.write_text("# Verifier Report\n\nNo verdict here.\n", encoding="utf-8")

    issues = validate(tmp_path)
    assert any("verifier report missing required section: Verdict" in issue for issue in issues)


def test_validator_rejects_receipt_that_disables_verifier(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    run_json = tmp_path / "fable5loop" / "runs" / "2026-07-05-scaffold-hardening-review" / "run.json"
    payload = load_json(run_json)
    payload["verifier"]["required"] = False
    write_json(run_json, payload)

    issues = validate(tmp_path)
    assert any("verifier.required must be true" in issue for issue in issues)


def test_validator_rejects_receipt_without_independent_verifier_context(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    run_json = tmp_path / "fable5loop" / "runs" / "2026-07-05-scaffold-hardening-review" / "run.json"
    payload = load_json(run_json)
    payload["verifier"]["independent_context"] = False
    write_json(run_json, payload)

    issues = validate(tmp_path)
    assert any("verifier.independent_context must be true" in issue for issue in issues)


def test_validator_rejects_outcome_template_missing_validation_output_section(tmp_path: Path) -> None:
    copy_scaffold(tmp_path)
    outcome = tmp_path / "fable5loop" / "outcomes" / "27vette-loop-outcomes.md"
    outcome.write_text(
        outcome.read_text(encoding="utf-8").replace("- Validation Output Inspected\n", ""),
        encoding="utf-8",
    )

    issues = validate(tmp_path)
    assert "outcome template missing phrase: Validation Output Inspected" in issues
