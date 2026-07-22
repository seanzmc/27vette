# Verifier Report — 2026-07-11 Grand Sport Jake-graphics ↔ heritage hash reverse exclusions

## Verdict

PASS (single cycle). Independent verifier subagent in a separate context; saw the spec, repo, and its own tool output only — no maker reasoning.

## Criteria

1. **Workbook truth — PASS.** openpyxl read (verifier's own): exactly 5 new groups `gs_group_{sht,pda,sne,vpo,vpw}_excludes_heritage_hash_and_z15` in `grandSport_rule_groups`, each `group_type=excludes_any`, `active=True`, correct `source_id` (opt_sht_001/opt_pda_001/opt_sne_001/opt_vpo_001/opt_vpw_001), correct disabled_reason text. `grandSport_rule_group_members`: each group has exactly 7 active rows, targets = `{opt_z15_001, opt_17a_001, opt_20a_001, opt_55a_001, opt_75a_001, opt_97a_001, opt_dx4_001}` exactly — no extras/omissions.
2. **Gates — PASS.** `validate_workbook_schema.py stingray_master.xlsx`: valid, 0 errors/warnings. `node --test tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs`: 25/25. `node --test tests/multi-model-runtime-switching.test.mjs`: 47/47. `.venv/bin/python -m pytest tests/ -k metadata -q`: 73 passed, 337 deselected.
3. **Companion-file scope — PASS.** `git status --porcelain`: modified `form-app/data.js`, `form-output/runtime/grand-sport-runtime-contract.json`, `form-output/workbook-edit-log.jsonl`, `stingray_master.xlsx`; untracked: the new spec doc and this run receipt dir (plus an unrelated pre-existing `.venv` local symlink, not part of the change). No runtime JS/CSS, dealer-submission code, or test files hand-edited.
4. **Browser proof — PASS.** Verifier independently drove the app (fresh Browser session): selected Grand Sport → Stripes step → clicked SNE via DOM `.click()`. All 6 hash marks (17A/20A/55A/75A/97A/DX4) flipped to `aria-disabled="true"` with tooltip `"SNE blocks Grand Sport Heritage Graphics and Heritage Hash Marks."`; deselecting SNE returned all 6 to `aria-disabled=null`. Spot-checked VPW independently: same disable/reason/re-enable behavior with `"VPW blocks Grand Sport Heritage Graphics and Heritage Hash Marks."`. Note: `opt_z15_001` has no standalone selectable button in the UI (includes-only auto-add per the spec's documented architecture, corroborated by the passing "Grand Sport heritage hash marks auto-add Z15..." test), so its `aria-disabled` state could not be DOM-queried directly — consistent with the documented design, not a gap.

## Evidence inspected

- `stingray_master.xlsx` sheets `grandSport_rule_groups` / `grandSport_rule_group_members` (openpyxl read-only probes, verifier's own).
- `git status --porcelain` output.
- `.hermes/plans/grand-sport-jake-heritage-hash-reverse-exclusions-spec.md`.
- Live app DOM state via `javascript_tool` (button `aria-disabled`, `outerHTML`, tooltip text) for SNE and VPW selections.

## Validation Output Inspected

- `validate_workbook_schema.py`: `"status": "valid"`, 0 errors/warnings.
- node --test (grand-sport-contract-preview + grand-sport-draft-data): 25/25.
- node --test (multi-model-runtime-switching): 47/47.
- pytest `-k metadata`: 73 passed, 337 deselected.

## Required Fixes Before Pass

None — single-cycle pass.

## Durable Lesson Candidates

None. The fix reused the repo's established explicit-reverse-group workbook convention and existing apply_workbook_ops/regenerate/gate pipeline. Screenshot rendering was blank in this session's Browser pane; the verifier worked around it with DOM/`aria-disabled` inspection via `javascript_tool`, which is situational tooling behavior for this session, not a new durable repo lesson (the skill already documents DOM/computed-style inspection over screenshot-trust for a related class of finding — "Invisible-not-empty UI reports").

## File Edit Statement

Verifier edited no files. All inspection was read-only; only the listed gates were executed, and the browser session only toggled option selections (no persisted state, no workbook writes).

## Notes (non-blocking)

- PDA and VPW are not disabled when Z15 or a hash mark is selected first (Z15's own reverse group `gs_group_z15_excludes_non_center_stripes` only targets stripes, not PDA/VPW) — pre-existing, unrelated to this pass, confirmed out of scope by inspecting that group's membership (unchanged by this pass).
