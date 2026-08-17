#!/usr/bin/env python3
"""The composed candidate lane (spec §3.7).

One operator-invocable, read-only command that takes a candidate workbook and
returns a pass/fail readiness verdict. Promotion preflight and the database
workflow's post-export gate both call this; neither reimplements the stage
sequence.

    python scripts/verify_workbook_candidate.py \
        --workbook <path> [--changed-model z06 ...] [--report <path>]

Every stage reads a temporary copy of the candidate workbook. Nothing here
writes a tracked path on any code path, including failure paths — the protected
surfaces are hashed on entry and re-checked on exit, and a mismatch is itself a
reported failure rather than something the caller has to notice.

Changed-model scoping is a reporting contract, not a generation filter (§3.7.1):
declaring a touched model never reduces what is generated, validated, or put in
the candidate registry. Its only effect is to partition the report, so that a
model nobody declared but whose contract moved is surfaced as `unexpected_drift`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.contract import load_model_asset_map
from corvette_form_generator.model_configs import ROOT, WORKBOOK_PATH, discover_generation_model_configs
from corvette_form_generator.model_generation import generate_model_artifacts
from corvette_form_generator.options_sheet_quality import lint_options_sheet_quality
from corvette_form_generator.output import write_app_data_registry
from corvette_form_generator.registry_promotion import (
    build_registry_from_artifacts,
    load_registry_promotions,
    registry_model_key,
    runtime_contract_artifact_path,
)
from corvette_form_generator.runtime_contract import assert_runtime_contract
from corvette_form_generator.schema_validation import validate_workbook_schema
from corvette_form_generator.workbook_package import validate_workbook_package

REPORT_SCHEMA_VERSION = "workbook-candidate-readiness-1"

# §3.7's stage list, in order. The report names the stage a failure came from,
# and stages after a failure do not run.
STAGES = (
    "copy_candidate",
    "workbook_package",
    "workbook_schema",
    "options_sheet_quality",
    "discover_models",
    "generate_models",
    "validate_contracts",
    "candidate_registry",
    # Checkpoint 2 of the fast layered validation suite added these two. The
    # snapshot is the independent expected side (§6.2); the parity stage is the
    # only place the lane compares source rows against what it just generated,
    # rather than against the retained artifact it is trying to replace.
    "workbook_truth",
    "source_parity",
    "browser_harness",
    "semantic_drift",
)

# Fields the candidate lane must ignore when asking whether a contract moved.
# Only generation timestamps — anything else is a real difference.
GENERATED_AT_KEYS = frozenset({"generated_at", "sourceGeneratedAt", "generatedAt"})

# The harness and parity stages run against the candidate registry. Kept as
# names so each override is a single fact, not a convention repeated in several
# places.
HARNESS_DATA_JS_ENV = "CORVETTE_FORM_DATA_JS"
WORKBOOK_TRUTH_ENV = "CORVETTE_WORKBOOK_TRUTH"
CONTRACT_ROOT_ENV = "CORVETTE_CONTRACT_ROOT"
DEFAULT_HARNESS = Path("tests/multi-model-runtime-switching.test.mjs")

# The §4.2 parity owners. They read the candidate's contracts and registry
# through the environment above, so the same files serve Layer 1 here and Layer
# 0 standalone against the tracked artifacts.
PARITY_GATES = (
    Path("tests/source-to-contract-parity.test.mjs"),
    Path("tests/source-to-registry-parity.test.mjs"),
)

# §3.7.1.1: a row in a global family marks every model touched, because a
# global-family edit can move a model nobody named.
ALL_MODELS = "*"


@dataclass
class StageResult:
    name: str
    ok: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"stage": self.name, "ok": self.ok, "findings": self.findings, "detail": self.detail}


class StageFailure(Exception):
    """Raised to stop the lane at the earliest stage that can see a defect."""

    def __init__(self, result: StageResult) -> None:
        super().__init__(f"stage {result.name} failed")
        self.result = result


def protected_surface_hashes(root: Path) -> dict[str, str]:
    paths = [root / "stingray_master.xlsx", root / "form-app" / "data.js"]
    paths.extend(
        path
        for path in (root / "form-output").rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    )
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
        if path.exists()
    }


def strip_generated_at(value: Any) -> Any:
    """Normalize a contract for semantic comparison.

    Dict keys are sorted and generation timestamps dropped; list order is
    preserved deliberately. Order is *not* semantic drift, so callers compare
    keyed entities rather than whole arrays — see `contract_entity_index`.
    """

    if isinstance(value, dict):
        return {key: strip_generated_at(value[key]) for key in sorted(value) if key not in GENERATED_AT_KEYS}
    if isinstance(value, list):
        return [strip_generated_at(item) for item in value]
    return value


# Identity per collection. Positional comparison would report a section reorder
# as drift for every downstream row; these are the columns that actually name a
# thing. A collection absent here is compared as an order-insensitive multiset.
ENTITY_KEYS: dict[str, tuple[str, ...]] = {
    "variants": ("variant_id",),
    "steps": ("step_key",),
    "sections": ("section_id",),
    "choices": ("choice_id",),
    "contextChoices": ("choice_id",),
    "standardEquipment": ("equipment_id",),
    "rules": ("rule_id",),
    "priceRules": ("price_rule_id",),
    "interiors": ("interior_id",),
    "ruleGroups": ("group_id",),
    "exclusiveGroups": ("group_id",),
    "defaultSelectionRules": ("rule_id",),
}


def _index_value(key: str, value: Any) -> Any:
    """Make one value order-insensitive but content- and cardinality-sensitive.

    Recurses into nested dicts, because a positional comparison of a *nested*
    list (`orderSummary.sections`) reports a reorder as drift just as wrongly as
    a top-level one would.
    """

    if isinstance(value, dict):
        return {inner: _index_value(inner, item) for inner, item in value.items()}
    if not isinstance(value, list):
        return value
    id_fields = ENTITY_KEYS.get(key)
    if id_fields and all(isinstance(row, dict) and all(f in row for f in id_fields) for row in value):
        keys = ["|".join(str(row[f]) for f in id_fields) for row in value]
        # Only key it if the identity is actually unique. Otherwise duplicate
        # rows would collapse into one entry and an added duplicate — a real
        # payload change — would read as no drift at all.
        if len(set(keys)) == len(keys):
            return dict(zip(keys, value))
    return sorted(json.dumps(row, sort_keys=True) for row in value)


def contract_entity_index(contract: dict[str, Any]) -> dict[str, Any]:
    """Reduce a contract to an order-insensitive, identity-keyed comparable."""

    return {key: _index_value(key, value) for key, value in strip_generated_at(contract).items()}


def semantic_drift(fresh: dict[str, Any], retained: dict[str, Any]) -> list[str]:
    """Collections whose identity-keyed content differs. Empty means no drift."""

    fresh_index = contract_entity_index(fresh)
    retained_index = contract_entity_index(retained)
    return sorted(
        key
        for key in set(fresh_index) | set(retained_index)
        if fresh_index.get(key) != retained_index.get(key)
    )


def declared_changed_set(changed_models: list[str], all_model_keys: set[str]) -> set[str]:
    if ALL_MODELS in changed_models:
        return set(all_model_keys)
    return {model for model in changed_models if model}


def run_stage_package(candidate: Path) -> StageResult:
    issues = validate_workbook_package(candidate)
    errors = [issue for issue in issues if str(issue.get("severity", "error")) == "error"]
    return StageResult(
        "workbook_package",
        ok=not errors,
        findings=[dict(issue) for issue in errors[:50]],
        detail={"issue_count": len(issues), "error_count": len(errors)},
    )


def run_stage_schema(candidate: Path) -> StageResult:
    # check_live_contract compares against the *published* tree, which a
    # candidate has no business being measured against. The candidate registry
    # is proven at stages 8 and 9 instead.
    issues = validate_workbook_schema(candidate, check_live_contract=False)
    errors = [issue for issue in issues if issue.severity == "error"]
    return StageResult(
        "workbook_schema",
        ok=not errors,
        findings=[
            {"severity": i.severity, "check_id": i.check_id, "sheet": i.sheet, "row": i.row, "message": i.message}
            for i in errors[:50]
        ],
        detail={"issue_count": len(issues), "error_count": len(errors)},
    )


def run_stage_options_quality(candidate: Path) -> StageResult:
    allowlist = ROOT / "tests" / "fixtures" / "options-sheet-quality-allowlist.json"
    issues = lint_options_sheet_quality(candidate, allowlist_path=allowlist if allowlist.exists() else None)
    return StageResult(
        "options_sheet_quality",
        ok=not issues,
        findings=[
            {"check_id": i.check_id, "model": i.model, "sheet": i.sheet, "row": i.row, "message": i.message}
            for i in issues[:50]
        ],
        detail={"issue_count": len(issues)},
    )


def retained_contract_for(model_key: str) -> dict[str, Any] | None:
    path = runtime_contract_artifact_path(ROOT, model_key)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_node_gates(stage: str, gates: tuple[Path, ...] | list[Path], env_overrides: dict[str, str]) -> StageResult:
    """Run node test files against the candidate, in one process."""

    import os
    import subprocess

    missing = [str(gate) for gate in gates if not gate.exists()]
    if missing:
        return StageResult(stage, ok=False, findings=[{"message": f"gate not found: {missing}"}])

    env = dict(os.environ)
    env.update(env_overrides)
    completed = subprocess.run(
        ["node", "--test", *[str(gate) for gate in gates]],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    ok = completed.returncode == 0
    return StageResult(
        stage,
        ok=ok,
        findings=[] if ok else [{"message": completed.stdout[-4000:] or completed.stderr[-4000:]}],
        detail={
            "gates": [str(gate) for gate in gates],
            "returncode": completed.returncode,
            **env_overrides,
        },
    )


def run_workbook_truth(candidate: Path, out_path: Path) -> StageResult:
    """Build the §6.2 snapshot from the candidate workbook, not the tracked one.

    Built here rather than inside each gate so Layer 1 pays it once and every
    parity assertion underneath compares against the same immutable document.
    """

    import subprocess

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "build_workbook_truth.py"),
            "--workbook",
            str(candidate),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return StageResult(
            "workbook_truth",
            ok=False,
            findings=[{"message": completed.stderr[-4000:] or completed.stdout[-4000:]}],
        )
    snapshot = json.loads(out_path.read_text(encoding="utf-8"))
    return StageResult(
        "workbook_truth",
        ok=True,
        detail={
            "snapshot": str(out_path),
            "schemaVersion": snapshot["schemaVersion"],
            "workbook_sha256": snapshot["workbook"]["sha256"],
            "sheets": len(snapshot["sheets"]),
            "models": sorted(snapshot["models"]),
            "promoted_models": snapshot["promotions"]["promoted_model_keys"],
        },
    )


def run_browser_harness(data_js: Path, harness: Path) -> StageResult:
    return run_node_gates("browser_harness", [harness], {HARNESS_DATA_JS_ENV: str(data_js)})


def verify_candidate(
    workbook: Path,
    *,
    changed_models: list[str] | None = None,
    report_path: Path | None = None,
    harness: Path | None = None,
    run_harness: bool = True,
) -> dict[str, Any]:
    """Run every §3.7 stage in order and return the readiness report."""

    changed_models = list(changed_models or [])
    harness = harness or (ROOT / DEFAULT_HARNESS)
    before = protected_surface_hashes(ROOT)
    stages: list[StageResult] = []
    models_report: dict[str, dict[str, Any]] = {}
    ok = True
    failed_stage = ""

    try:
      with tempfile.TemporaryDirectory(prefix="candidate-verify-") as tmpdir:
          tmp = Path(tmpdir)
          candidate_root = tmp / "candidate"
          workbook_dir = candidate_root
          workbook_dir.mkdir(parents=True)
          # Keep the canonical filename: dataset.source_workbook records it.
          candidate = workbook_dir / WORKBOOK_PATH.name
          shutil.copy2(workbook, candidate)
          stages.append(
              StageResult("copy_candidate", ok=True, detail={"source": str(workbook), "candidate": str(candidate)})
          )

          try:
              for runner in (run_stage_package, run_stage_schema, run_stage_options_quality):
                  result = runner(candidate)
                  stages.append(result)
                  if not result.ok:
                      raise StageFailure(result)

              configs = discover_generation_model_configs(candidate, root=candidate_root)
              stages.append(
                  StageResult("discover_models", ok=bool(configs), detail={"models": sorted(configs)})
              )
              if not configs:
                  raise StageFailure(stages[-1])

              declared = declared_changed_set(changed_models, set(configs))
              undeclared_names = sorted(set(changed_models) - set(configs) - {ALL_MODELS})
              if undeclared_names:
                  result = StageResult(
                      "discover_models",
                      ok=False,
                      findings=[{"message": f"--changed-model names unknown models: {undeclared_names}"}],
                  )
                  stages.append(result)
                  raise StageFailure(result)

              # Stage 6: generate EVERY discovered model. `declared` is never
              # consulted here — that is the whole point of §3.7.1.
              generation_findings: list[dict[str, Any]] = []
              summaries: dict[str, dict[str, Any]] = {}
              for model_key in sorted(configs):
                  try:
                      summaries[model_key] = generate_model_artifacts(configs[model_key])
                  except Exception as exc:  # noqa: BLE001 - reported, not swallowed
                      generation_findings.append({"model_key": model_key, "message": f"{type(exc).__name__}: {exc}"})
              result = StageResult(
                  "generate_models",
                  ok=not generation_findings,
                  findings=generation_findings,
                  detail={"generated": sorted(summaries)},
              )
              stages.append(result)
              if not result.ok:
                  raise StageFailure(result)

              # Stage 7: strict validation of every exact contract, config-bound.
              validation_findings: list[dict[str, Any]] = []
              for model_key in sorted(configs):
                  contract_path = Path(summaries[model_key]["runtime_contract_json"])
                  contract = json.loads(contract_path.read_text(encoding="utf-8"))
                  try:
                      assert_runtime_contract(
                          contract,
                          source=f"candidate {model_key}",
                          config=configs[model_key],
                      )
                  except ValueError as exc:
                      validation_findings.append({"model_key": model_key, "message": str(exc)})

                  retained = retained_contract_for(model_key)
                  drift = semantic_drift(contract, retained) if retained is not None else []
                  models_report[model_key] = {
                      "model_key": model_key,
                      "generated": True,
                      "validation_findings": [
                          f["message"] for f in validation_findings if f["model_key"] == model_key
                      ],
                      "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                      "declared_changed": model_key in declared,
                      "semantic_drift_vs_retained": drift,
                      "retained_contract_present": retained is not None,
                  }
              result = StageResult(
                  "validate_contracts",
                  ok=not validation_findings,
                  findings=validation_findings,
              )
              stages.append(result)
              if not result.ok:
                  raise StageFailure(result)

              # Stage 8: a complete candidate registry from exactly those fresh
              # contracts, written inside the temporary root.
              candidate_app_dir = candidate_root / "form-app"
              candidate_app_dir.mkdir(parents=True, exist_ok=True)
              candidate_data_js = candidate_app_dir / "data.js"
              registry_findings: list[dict[str, Any]] = []
              promoted: list[str] = []
              try:
                  wb = load_workbook(candidate, read_only=True, data_only=True)
                  try:
                      promotions = load_registry_promotions(wb)
                      model_assets = load_model_asset_map(wb, registry_model_key)
                      registry = build_registry_from_artifacts(
                          wb, model_assets=model_assets, root=candidate_root
                      )
                  finally:
                      wb.close()
                  promoted = sorted(registry.get("models", {}))
                  # Exactly-one-default is enforced by load_registry_promotions();
                  # re-checking it here would be a second acceptance check that
                  # can never fire (§3.8's standing rule).
                  del promotions
                  legacy_aliases = registry.pop("legacyAliases", {})
                  write_app_data_registry(candidate_data_js, registry, legacy_aliases=legacy_aliases)
              except Exception as exc:  # noqa: BLE001
                  registry_findings.append({"message": f"{type(exc).__name__}: {exc}"})
              result = StageResult(
                  "candidate_registry",
                  ok=not registry_findings,
                  findings=registry_findings,
                  detail={"data_js": str(candidate_data_js), "models": promoted},
              )
              stages.append(result)
              if not result.ok:
                  raise StageFailure(result)

              # Stage 9: the independent workbook-truth snapshot (§6.2), built
              # from the CANDIDATE workbook. Building it from the tracked one
              # would have the parity stage below check fresh output against a
              # different workbook's rows.
              truth_path = tmp / "workbook-truth.json"
              result = run_workbook_truth(candidate, truth_path)
              stages.append(result)
              if not result.ok:
                  raise StageFailure(result)

              # Stage 10: parity between those source rows and what stages 6-8
              # just produced. Every path is inside the temporary root, so this
              # proves the candidate rather than the retained artifacts.
              result = run_node_gates(
                  "source_parity",
                  PARITY_GATES,
                  {
                      WORKBOOK_TRUTH_ENV: str(truth_path),
                      CONTRACT_ROOT_ENV: str(candidate_root),
                      HARNESS_DATA_JS_ENV: str(candidate_data_js),
                  },
              )
              stages.append(result)
              if not result.ok:
                  raise StageFailure(result)

              # Stage 11: the browser harness, against the candidate registry.
              if run_harness:
                  result = run_browser_harness(candidate_data_js, harness)
                  stages.append(result)
                  if not result.ok:
                      raise StageFailure(result)

          except StageFailure as failure:
              ok = False
              failed_stage = failure.result.name

    except BaseException as exc:  # noqa: BLE001
        # The boundary claim must hold on EVERY exit path, including an
        # unexpected exception and a Ctrl-C mid-stage. Check it, report it, then
        # let the original exception continue.
        violations = sorted(
            key
            for key in set(before) | set(protected_surface_hashes(ROOT))
            if before.get(key) != protected_surface_hashes(ROOT).get(key)
        )
        if violations:
            raise RuntimeError(
                f"candidate lane aborted with {type(exc).__name__} AND modified protected paths: {violations}"
            ) from exc
        raise

    # §3.7.1.3: an undeclared model whose contract moved fails the run. Only
    # meaningful once the staged run reached validation; after an earlier stage
    # failure there is nothing to partition and stage 10 must not run.
    unexpected_drift = sorted(
        key
        for key, row in models_report.items()
        if row["semantic_drift_vs_retained"] and not row["declared_changed"]
    )
    if models_report and not failed_stage:
        stages.append(
            StageResult(
                "semantic_drift",
                ok=not unexpected_drift,
                findings=[
                    {
                        "model_key": key,
                        "message": (
                            f"{key} was not declared changed but its contract differs from the retained "
                            f"artifact in: {', '.join(models_report[key]['semantic_drift_vs_retained'])}"
                        ),
                    }
                    for key in unexpected_drift
                ],
            )
        )
    if unexpected_drift and not failed_stage:
        ok = False
        failed_stage = "semantic_drift"

    after = protected_surface_hashes(ROOT)
    boundary_violations = sorted(
        key for key in set(before) | set(after) if before.get(key) != after.get(key)
    )
    if boundary_violations:
        ok = False
        failed_stage = failed_stage or "boundary"

    report = {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "ok": ok,
        "workbook": str(workbook),
        "failedStage": failed_stage,
        "stagesRun": [stage.name for stage in stages],
        "stagesNotRun": [name for name in STAGES if name not in {stage.name for stage in stages}],
        "stagesSkippedByCaller": [] if run_harness else ["browser_harness"],
        "stages": [stage.as_dict() for stage in stages],
        "declaredChangedModels": sorted(declared_changed_set(changed_models, set(models_report))),
        "models": models_report,
        "partition": {
            "changed": sorted(k for k, r in models_report.items() if r["declared_changed"]),
            "unchanged": sorted(
                k
                for k, r in models_report.items()
                if not r["declared_changed"] and not r["semantic_drift_vs_retained"]
            ),
            "unexpected_drift": unexpected_drift,
        },
        "boundaryViolations": boundary_violations,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workbook", type=Path, default=WORKBOOK_PATH)
    parser.add_argument(
        "--changed-model",
        action="append",
        default=[],
        help=f"model_key touched by the change; {ALL_MODELS!r} marks every model touched",
    )
    parser.add_argument("--report", type=Path, help="write the readiness report JSON here")
    parser.add_argument("--harness", type=Path, help=f"node test file to run (default {DEFAULT_HARNESS})")
    parser.add_argument("--skip-harness", action="store_true", help="skip stage 9 (diagnostics only)")
    args = parser.parse_args(argv)

    report = verify_candidate(
        args.workbook,
        changed_models=args.changed_model,
        report_path=args.report,
        harness=args.harness,
        run_harness=not args.skip_harness,
    )
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
