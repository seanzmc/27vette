#!/usr/bin/env python3
"""Verify the exact Pass 4 Stage C docs/path implementation manifest."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "fable5loop/runs/2026-07-29-pass4c-stagec-implementation"
SNAPSHOT = json.loads((RUN / "source-snapshot.json").read_text())

PLAN_MOVES = [
    "asset-map-exterior-color-url-refresh.md",
    "asset-map-sync-legacy-retirement-pass3-spec.md",
    "color-override-normalization-spec.md",
    "cross-model-stale-gate-expectations-spec.md",
    "fable5-source-doc-rename-pass7-spec.md",
    "form-mobile-ux-consistency-spec.md",
    "generator-simplification-pass2-runtime-payload-trim.md",
    "grand-sport-z06-stripe-workbook-rule-fix.md",
    "live-deltas-into-local-spec.md",
    "live-runtime-merge-readiness-no-behavior-change-spec.md",
    "paint-accent-progress-checkmarks-spec.md",
    "r6x-interior-components-spec.md",
    "route-map-condensation-pass6-spec.md",
    "rule-audit-orphan-retirement-pass2-spec.md",
    "src-images-retirement-pass5-spec.md",
    "stingray-engine-appearance-display-order-match-grand-sport.md",
    "superpowers-untrack-pass1-spec.md",
    "vehicle-setup-copy-workbook-ownership-spec.md",
    "z06-runtime-rule-correction-spec.md",
]
ACTIVE_PLANS = [
    "grand-sport-jake-heritage-hash-reverse-exclusions-spec.md",
    "grand-sport-stripe-heritage-reverse-exclusions-spec.md",
    "layered-visualizer-integration-spec.md",
    "rule-normalization-pass1-redundant-exclusive-excludes.md",
    "rule-normalization-pass2-grouped-excludes.md",
    "rule-normalization-pass7b-failed-fix-correction.md",
    "z06-carbon-wheel-package-disabled-state-spec.md",
    "z06-interior-accessory-cleanup-pass2-spec.md",
    "z06-package-pricing-cascade-spec.md",
]
CLOSE_THEN_ARCHIVE = [
    "asset-map-exterior-color-url-refresh.md",
    "color-override-normalization-spec.md",
    "generator-simplification-pass2-runtime-payload-trim.md",
    "grand-sport-z06-stripe-workbook-rule-fix.md",
    "live-deltas-into-local-spec.md",
    "live-runtime-merge-readiness-no-behavior-change-spec.md",
    "r6x-interior-components-spec.md",
    "stingray-engine-appearance-display-order-match-grand-sport.md",
    "z06-runtime-rule-correction-spec.md",
]
DOC_MOVES = {
    "docs/db_audit-7-22.md": "docs/archive/old-reports/db_audit-7-22.md",
    "docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md": "docs/archive/completed-specs/workbook-manager/2026-07-16-workbook-congruent-relational-database.md",
    "docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md": "docs/archive/completed-specs/workbook-manager/2026-07-16-workbook-congruent-relational-database-design.md",
    "docs/react-editor prompt.md": "docs/archive/completed-specs/workbook-manager/react-editor-prompt.md",
}
DELETIONS = [
    "docs/claude_output-workbookEditor.md",
    "fable5loop/runs/2026-07-05-cross-model-regression-hardening/multi-model-runtime-switching-full.log",
    "fable5loop/runs/2026-07-05-cross-model-regression-hardening/stingray-form-regression-full.log",
]
OLD_PATHS = [
    *(f".hermes/plans/{name}" for name in PLAN_MOVES),
    *DOC_MOVES,
    *DELETIONS,
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors: list[str] = []
    actual = sorted(path.name for path in (ROOT / ".hermes/plans").glob("*.md"))
    if actual != sorted(ACTIVE_PLANS):
        errors.append(f"active plan mismatch: {actual!r}")

    archive_root = ROOT / "docs/archive/completed-specs"
    for name in PLAN_MOVES:
        if (ROOT / ".hermes/plans" / name).exists():
            errors.append(f"old plan exists: {name}")
        if not (archive_root / name).is_file():
            errors.append(f"archived plan missing: {name}")

    for source, destination in DOC_MOVES.items():
        if (ROOT / source).exists():
            errors.append(f"old document exists: {source}")
        if not (ROOT / destination).is_file():
            errors.append(f"moved document missing: {destination}")

    for path in DELETIONS:
        if (ROOT / path).exists():
            errors.append(f"deleted path exists: {path}")

    closure_marker = "Archive closure (2026-07-29): COMPLETED"
    for name in CLOSE_THEN_ARCHIVE:
        count = (archive_root / name).read_text().count(closure_marker)
        if count != 1:
            errors.append(f"closure marker count {count}: {name}")

    for path, expected in SNAPSHOT["protected"].items():
        candidate = ROOT / path
        if not candidate.is_file() or digest(candidate) != expected:
            errors.append(f"protected drift: {path}")

    for path, expected in SNAPSHOT["preexisting_archives"].items():
        candidate = ROOT / path
        if not candidate.is_file() or digest(candidate) != expected:
            errors.append(f"pre-existing archive drift: {path}")

    allowed = set(SNAPSHOT["allowed_prior_receipt_change"])
    ignored = set(SNAPSHOT["ignored_metadata_basenames"])
    checked_receipts = 0
    for path, expected in SNAPSHOT["prior_receipts"].items():
        if path in allowed or Path(path).name in ignored:
            continue
        checked_receipts += 1
        candidate = ROOT / path
        if not candidate.is_file() or digest(candidate) != expected:
            errors.append(f"prior receipt drift: {path}")

    verifier = ROOT / "fable5loop/runs/2026-07-05-cross-model-regression-hardening/verifier-report.md"
    if verifier.read_text().count("## Raw-log retirement note — 2026-07-29") != 1:
        errors.append("raw-log retirement note missing or duplicated")

    name_status = subprocess.check_output(
        ["git", "diff", "--name-status", "-M", "HEAD"], cwd=ROOT, text=True
    ).splitlines()
    renames = [line for line in name_status if line.startswith("R")]
    deletions = [line for line in name_status if line.startswith("D\t")]
    if len(renames) != 23:
        errors.append(f"combined HEAD diff has {len(renames)} renames, expected 23")
    deleted_paths = sorted(line.split("\t", 1)[1] for line in deletions)
    if deleted_paths != sorted(DELETIONS):
        errors.append(f"combined HEAD diff deletion mismatch: {deletions!r}")

    tracked_and_untracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    active_hits: list[tuple[str, str, int]] = []
    spec_path = "docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md"
    for relative in tracked_and_untracked:
        if relative.startswith("docs/archive/") or relative.startswith("fable5loop/runs/"):
            continue
        if relative == "fable5loop/STATE.md":
            continue
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for old_path in OLD_PATHS:
            count = text.count(old_path)
            if not count:
                continue
            if relative == spec_path and old_path in DELETIONS and count == 1:
                continue
            active_hits.append((relative, old_path, count))
    if active_hits:
        errors.append(f"current non-historical old-path hits: {active_hits!r}")

    result = {
        "active_plans": len(actual),
        "plan_moves": len(PLAN_MOVES),
        "document_moves": len(DOC_MOVES),
        "deletions": len(DELETIONS),
        "closure_notes": len(CLOSE_THEN_ARCHIVE),
        "protected_files": len(SNAPSHOT["protected"]),
        "preexisting_archive_files": len(SNAPSHOT["preexisting_archives"]),
        "prior_receipt_files_checked": checked_receipts,
        "ignored_metadata_basenames": sorted(ignored),
        "combined_diff_renames": len(renames),
        "combined_diff_deletions": len(deletions),
        "current_nonhistorical_old_path_hits": len(active_hits),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
