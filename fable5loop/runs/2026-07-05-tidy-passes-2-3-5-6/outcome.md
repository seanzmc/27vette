# Outcome rubric · 2026-07-05 simplification passes 2, 3, 5, 6

Task-specific derivative of `fable5loop/outcomes/27vette-loop-outcomes.md`. Written before any repo edit.

## Task summary

- Goal: after committing passes 4+7, implement the four remaining simplification-audit passes: Pass 2 (orphan Grand Sport rule-audit artifacts + dead generator metadata), Pass 3 (legacy `asset_map-Sync/` entrypoint retirement), Pass 5 (unreferenced `src/*.png` retirement), Pass 6 (route-map doc condensation).
- Changed surface: stale generated inspection artifacts (orphaned, no writer), one dead generator helper + result key, legacy stub script + its guard test, doc moves/condensation, README dirs line, loop artifacts.
- Source-of-truth decision: workbook untouched; generated runtime/registry artifacts untouched (only orphaned inspection artifacts with no writer are removed, per audit claim 2); docs archived per the 2026-06-27 delete/archive precedent.
- Protected boundaries: workbook, live generated artifacts (`form-output/runtime/`, `form-output/stingray-form-data.*`, `form-app/data.js`), runtime app behavior, styling, dealer submission, ingest — untouched.
- Specs: `.hermes/plans/rule-audit-orphan-retirement-pass2-spec.md`, `.hermes/plans/asset-map-sync-legacy-retirement-pass3-spec.md`, `.hermes/plans/src-images-retirement-pass5-spec.md`, `.hermes/plans/route-map-condensation-pass6-spec.md`.

## Required outcome criteria

1. Each pass has a written spec (exact files, exact changes, gates) before its edits.
2. Pass 2: `form-output/inspection/grand-sport-rule-audit.json/.md` removed; `_rule_audit_artifacts()` and the `rule_audit_artifacts` result key removed from `model_generation.py`; `REQUIRED_RESULT_KEYS` untouched; no remaining active references.
3. Pass 3: `asset_map-Sync/` directory gone; README content preserved at `docs/asset-map-sync.md` (git rename); guard test now asserts the legacy path stays absent; root `README.md` dirs line updated.
4. Pass 5: all 44 `src/*.png` removed from tracking and working tree; `src/` gone; root `README.md` dirs line updated; zero tracked references broken (audit claim 4: there were none).
5. Pass 6: `docs/Audit-route-map.md` + `docs/audit-cleanup-overview.md` archived as git renames under `docs/archive/completed-specs/audit-cleanup/`; a condensed active `docs/route-map.md` exists carrying current route, philosophy constraints, and the open candidates verbatim in substance.
6. Validation is real: named gates run with captured output; gate-induced generated-artifact churn restored before verification (known failure mode); pre-existing failures reported honestly, not fixed silently.
7. Generated live surfaces diff-empty against HEAD at closeout (`form-output/runtime/`, `form-output/stingray-form-data.*`, `form-app/`, `stingray_master.xlsx`).
8. Independent verifier (separate context, no maker reasoning) grades all criteria and returns a written verdict before closeout.
9. Memory compounds: STATE verified facts + Last session updated with ISO dates and Evidence refs; skill-update decision recorded with evidence.
10. Loop gate `.venv/bin/python scripts/validate_fable5_loop.py` passes after receipt/STATE writes.

## Result

All criteria met. Verifier: initial FAIL on criteria 1/7 (staging incompleteness — plain edits and the new doc were not in the index while completion records claimed "staged"); maker staged all pass files and adopted the flagged route-map omission (open candidate 6); read-only re-grade → final verdict PASS (8/8). Skill updated with the completion-record staging-drift failure mode. See `verifier-report.md`.
