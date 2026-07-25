# Outcome rubric — Pass 1: shared registry is the only workbook-shape authority

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §4 Pass 1.

Pass 1 is the post-export gate for the database-backed workbook editor. Before this
pass, `validate_workbook_schema.py stingray_master.xlsx` reported zero issues while
real per-model shape drift existed (§2.1.1), because workbook shape was owned in four
places at once.

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | `schema_validation.py` holds no independent header/artifact-type authority; its constants are the shared registry objects | PASS — `MODEL_MASTER_HEADERS`, `MODEL_REGISTRY_PROMOTION_HEADERS`, `MODEL_SETUP_COPY_FIELDS`, `VALID_REGISTRY_PROMOTION_ARTIFACT_TYPES` all derive from `workbook_domain.registry` |
| 2 | `registry_promotion.py` holds no independent header/artifact-type authority | PASS — same three constants derived |
| 3 | Registry owns the promotable artifact-type domain | PASS — `REGISTRY_PROMOTION_ARTIFACT_TYPES` + `model_registry_promotion.enums.artifact_type` |
| 4 | A registered active sheet missing a registry-owned column is an error | PASS — `registry_family_columns_missing` |
| 5 | A rogue physical column on a registered active sheet is an error | PASS — `registry_family_columns_unregistered` |
| 6 | A rename applied to **every** active sheet at once is rejected (cross-sheet equality passes; only registry ownership catches it) | PASS — RED proved `issues == []` before the change |
| 7 | `editor_ops` rejects a write to a physical column outside the registry | PASS — RED proved `errors == []` before the change |
| 8 | Workbook Manager carries no hand-authored column metadata | PASS — `_SECTION_SPEC` derives from `READONLY_SHEET_META` |
| 9 | Registry exposes the family-to-model mapping §3.7.1 needs, widening (never narrowing) on global families | PASS — `models_for_write_targets()` |
| 10 | Canonical workbook still validates | PASS — package valid / 0 issues; schema `--skip-live-contract` valid / 0 issues |
| 11 | No new test failure versus the recorded baseline | PASS — same 6 pre-existing Python failures (four editor lint/compare, two retained-artifact source-assembly); both node failures reproduce with the change stashed. Note: `validation-output.txt` shows 7 in the intermediate runs because `test_fable5_loop_contract` was red until this receipt was complete; it is green in the final run. |
| 12 | No workbook, generated-artifact, registry, or dealer write | PASS — protected surfaces byte-clean; workbook SHA unchanged |

## Explicitly out of scope

Source-builder convergence (Pass 2), the retained Stingray contract migration and the
composed candidate verifier (Pass 3), any deletion (Pass 4), model data repair, artifact
refresh, promotion, publication.
