#!/usr/bin/env python3
"""Validate the repo-local Fable 5 compounding-loop scaffold."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "fable5loop" / "fable5-loop-contract.json"
CANONICAL_COMMAND = ".venv/bin/python scripts/validate_fable5_loop.py"
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?\b")
RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _has_heading(text: str, heading: str) -> bool:
    return f"## {heading}" in text or f"# {heading}" in text


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


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _repo_path_exists(root: Path, relative: Any) -> bool:
    return isinstance(relative, str) and bool(relative) and (root / relative).is_file()


def _validate_command_surface(root: Path, contract: dict[str, Any], issues: list[str]) -> None:
    readme_path = root / "README.md"
    if readme_path.is_file():
        if CANONICAL_COMMAND not in readme_path.read_text(encoding="utf-8"):
            issues.append(f"README.md missing canonical validator command: {CANONICAL_COMMAND}")
    else:
        issues.append("missing README.md")

    for relative in (
        contract.get("entrypoint"),
        contract.get("skillFile"),
        contract.get("routineTemplate"),
    ):
        path = root / str(relative)
        if path.is_file() and CANONICAL_COMMAND not in path.read_text(encoding="utf-8"):
            issues.append(f"{relative} missing canonical validator command: {CANONICAL_COMMAND}")

    loop_root = root / "fable5loop"
    if not loop_root.is_dir():
        return
    for path in loop_root.rglob("*.md"):
        if "Attachments" in path.parts:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "scripts/validate_fable5_loop.py" not in line:
                continue
            if CANONICAL_COMMAND in line:
                continue
            stripped = line.strip()
            lower = stripped.lower()
            looks_like_command = (
                bool(re.search(r"\brun\s+`?(?:\.\./)?scripts/validate_fable5_loop\.py", lower))
                or "command" in lower
                or stripped.startswith("scripts/validate_fable5_loop.py")
                or stripped.startswith("../scripts/validate_fable5_loop.py")
                or stripped.startswith("`scripts/validate_fable5_loop.py")
                or stripped.startswith("`../scripts/validate_fable5_loop.py")
            )
            if looks_like_command:
                issues.append(f"direct validator invocation in {path.relative_to(root)}:{line_number}")


def _validate_state(root: Path, contract: dict[str, Any], issues: list[str]) -> None:
    state_path = root / contract.get("stateFile", "")
    if not state_path.is_file():
        issues.append(f"missing stateFile: {contract.get('stateFile')}")
        return

    state_text = state_path.read_text(encoding="utf-8")
    for section in contract.get("stateRequiredSections", []):
        if not _has_heading(state_text, section):
            issues.append(f"STATE.md missing section: {section}")

    for section in contract.get("memoryEvidenceRequiredSections", []):
        for bullet in _bullet_texts(state_text, section):
            if not DATE_RE.search(bullet):
                issues.append(f"STATE.md {section} bullet missing ISO date: {bullet}")
            if "Evidence:" not in bullet:
                issues.append(f"STATE.md {section} bullet missing Evidence: {bullet}")

    latest = _latest_run_dir(root, contract)
    if latest is None:
        return
    last_session = "\n".join(_section_lines(state_text, "Last session"))
    latest_relative = latest.relative_to(root).as_posix()
    if latest_relative not in last_session:
        issues.append(f"STATE.md Last session does not reference latest run folder: {latest_relative}")


def _run_dirs(root: Path, contract: dict[str, Any]) -> list[Path]:
    runs_dir = root / contract.get("runsDirectory", "fable5loop/runs")
    if not runs_dir.is_dir():
        return []
    return sorted(path for path in runs_dir.iterdir() if path.is_dir() and RUN_DIR_RE.match(path.name))


def _latest_run_dir(root: Path, contract: dict[str, Any]) -> Path | None:
    runs = _run_dirs(root, contract)
    return runs[-1] if runs else None


def _validate_run_receipts(root: Path, contract: dict[str, Any], issues: list[str]) -> None:
    runs_dir = root / contract.get("runsDirectory", "fable5loop/runs")
    if not runs_dir.is_dir():
        issues.append(f"missing runsDirectory: {runs_dir.relative_to(root)}")
        return

    template = contract.get("runReceiptTemplate")
    if not _repo_path_exists(root, template):
        issues.append(f"missing runReceiptTemplate: {template}")

    run_dirs = _run_dirs(root, contract)
    if not run_dirs:
        issues.append(f"no run receipt folders found under: {runs_dir.relative_to(root)}")
        return

    for run_dir in run_dirs:
        run_label = run_dir.relative_to(root).as_posix()
        for filename in contract.get("runReceiptRequiredFiles", []):
            if not (run_dir / filename).is_file():
                issues.append(f"missing run receipt artifact: {run_label}/{filename}")

        run_json_path = run_dir / "run.json"
        if not run_json_path.is_file():
            continue
        try:
            run_json = _load_json(run_json_path)
        except json.JSONDecodeError as exc:
            issues.append(f"{run_label}/run.json is not valid JSON: {exc}")
            continue

        for field in contract.get("runReceiptRequiredFields", []):
            if field not in run_json:
                issues.append(f"{run_label}/run.json missing field: {field}")

        if run_json.get("id") != run_dir.name:
            issues.append(f"{run_label}/run.json id does not match folder name")

        started_at = _parse_timestamp(run_json.get("started_at"))
        completed_at = _parse_timestamp(run_json.get("completed_at"))
        if started_at is None:
            issues.append(f"{run_label}/run.json started_at is not ISO timestamp")
        if completed_at is None:
            issues.append(f"{run_label}/run.json completed_at is not ISO timestamp")
        if started_at and completed_at and completed_at < started_at:
            issues.append(f"{run_label}/run.json completed_at is earlier than started_at")

        for field in ("outcome_rubric", "verifier_report", "validation_output"):
            if not _repo_path_exists(root, run_json.get(field)):
                issues.append(f"{run_label}/run.json {field} path does not exist: {run_json.get(field)}")

        state_updates = run_json.get("state_updates")
        if not isinstance(state_updates, list) or not state_updates:
            issues.append(f"{run_label}/run.json state_updates must be a non-empty list")
        else:
            for index, update in enumerate(state_updates):
                evidence = update.get("evidence") if isinstance(update, dict) else None
                if not _repo_path_exists(root, evidence):
                    issues.append(f"{run_label}/run.json state_updates[{index}].evidence path does not exist: {evidence}")

        skill_update = run_json.get("skill_update")
        if not isinstance(skill_update, dict):
            issues.append(f"{run_label}/run.json skill_update must be an object")
        else:
            decision = skill_update.get("decision")
            if decision not in contract.get("skillUpdateDecisions", []):
                issues.append(f"{run_label}/run.json skill_update.decision is invalid: {decision}")
            evidence = skill_update.get("evidence")
            if not _repo_path_exists(root, evidence):
                issues.append(f"{run_label}/run.json skill_update.evidence path does not exist: {evidence}")

        verifier = run_json.get("verifier")
        if not isinstance(verifier, dict):
            issues.append(f"{run_label}/run.json verifier must be an object")
        else:
            verdict = verifier.get("verdict")
            if verdict not in contract.get("verifierVerdicts", []):
                issues.append(f"{run_label}/run.json verifier.verdict is invalid: {verdict}")
            if verifier.get("required") is not True:
                issues.append(f"{run_label}/run.json verifier.required must be true")
            if verifier.get("independent_context") is not True:
                issues.append(f"{run_label}/run.json verifier.independent_context must be true")
            report_path = root / str(run_json.get("verifier_report", ""))
            _validate_verifier_report(report_path, run_label, issues)


def _validate_verifier_report(report_path: Path, run_label: str, issues: list[str]) -> None:
    if not report_path.is_file():
        return
    text = report_path.read_text(encoding="utf-8")
    for section in (
        "Verdict",
        "Criteria",
        "Evidence inspected",
        "Validation Output Inspected",
        "Required Fixes Before Pass",
        "Durable Lesson Candidates",
        "File Edit Statement",
    ):
        if not _has_heading(text, section):
            issues.append(f"{run_label} verifier report missing required section: {section}")


def _validate_rubric(root: Path, contract: dict[str, Any], issues: list[str]) -> None:
    rubric_path = root / contract.get("evalRubric", "")
    if not rubric_path.is_file():
        issues.append(f"missing evalRubric: {contract.get('evalRubric')}")
        return
    try:
        rubric = _load_json(rubric_path)
    except json.JSONDecodeError as exc:
        issues.append(f"eval rubric is not valid JSON: {exc}")
        return

    criteria_ids = {criterion.get("id") for criterion in rubric.get("criteria", [])}
    for required_id in (
        "three_tiers_present",
        "four_layers_present",
        "independent_verifier_required",
        "state_memory_progression",
        "skill_distillation_path",
        "validator_passes",
        "run_receipts_required",
        "timestamped_memory_evidence",
        "verifier_proof_recorded",
        "skill_update_decision_recorded",
    ):
        if required_id not in criteria_ids:
            issues.append(f"eval rubric missing criterion: {required_id}")
    if rubric.get("max_iterations") != contract.get("maxIterationsDefault"):
        issues.append("eval rubric max_iterations does not match contract maxIterationsDefault")


def validate(root: Path = ROOT) -> list[str]:
    """Return structural issues for the Fable 5 loop scaffold."""

    issues: list[str] = []
    contract_path = root / "fable5loop" / "fable5-loop-contract.json"
    if not contract_path.is_file():
        return [f"missing contract: {contract_path}"]

    try:
        contract = _load_json(contract_path)
    except json.JSONDecodeError as exc:
        return [f"contract is not valid JSON: {exc}"]

    tiers = contract.get("tiers", [])
    if len(tiers) != 3:
        issues.append(f"expected exactly 3 tiers, found {len(tiers)}")

    layers = contract.get("compoundStack", [])
    if len(layers) != 4:
        issues.append(f"expected exactly 4 compound-stack layers, found {len(layers)}")

    layer_ids = {layer.get("id") for layer in layers}
    for tier in tiers:
        coverage = tier.get("layerCoverage", [])
        if not coverage:
            issues.append(f"tier {tier.get('id', '<missing>')} has no layerCoverage")
        unknown = [layer for layer in coverage if layer not in layer_ids]
        if unknown:
            issues.append(f"tier {tier.get('id', '<missing>')} references unknown layers: {unknown}")
        if not tier.get("requiredPractices"):
            issues.append(f"tier {tier.get('id', '<missing>')} has no requiredPractices")

    for relative in contract.get("requiredArtifacts", []):
        if not (root / relative).is_file():
            issues.append(f"missing required artifact: {relative}")

    source_document = contract.get("sourceDocument")
    if not source_document or not (root / source_document).is_file():
        issues.append(f"missing sourceDocument: {source_document}")

    skill_path = root / contract.get("skillFile", "")
    if skill_path.is_file():
        skill_text = skill_path.read_text(encoding="utf-8")
        for section in contract.get("skillRequiredSections", []):
            if not _has_heading(skill_text, section):
                issues.append(f"skill missing section: {section}")
        for required_phrase in ("independent verifier", "State update contract", "Skill improvement contract"):
            if required_phrase not in skill_text:
                issues.append(f"skill missing phrase: {required_phrase}")
    else:
        issues.append(f"missing skillFile: {contract.get('skillFile')}")

    outcome_path = root / contract.get("outcomeTemplate", "")
    if outcome_path.is_file():
        outcome_text = outcome_path.read_text(encoding="utf-8")
        for required_phrase in (
            "independent verifier",
            "Max iterations",
            "Stop conditions",
            "Validation Output Inspected",
            "Explicit statement that the verifier did not edit files",
        ):
            if required_phrase not in outcome_text:
                issues.append(f"outcome template missing phrase: {required_phrase}")
    else:
        issues.append(f"missing outcomeTemplate: {contract.get('outcomeTemplate')}")

    routine_path = root / contract.get("routineTemplate", "")
    if routine_path.is_file():
        routine_text = routine_path.read_text(encoding="utf-8")
        for required_phrase in ("Trigger", "Run protocol", "Write before walking away", "Guardrails"):
            if required_phrase not in routine_text:
                issues.append(f"routine template missing phrase: {required_phrase}")
    else:
        issues.append(f"missing routineTemplate: {contract.get('routineTemplate')}")

    _validate_command_surface(root, contract, issues)
    _validate_state(root, contract, issues)
    _validate_run_receipts(root, contract, issues)
    _validate_rubric(root, contract, issues)

    return issues


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    issues = validate(root)
    if issues:
        print("Fable 5 loop validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Fable 5 loop validation passed: 3 tiers, 4 layers, required artifacts, memory, skill, routine, outcomes, and eval rubric are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
