# Grand Sport: Jake graphics (SHT/PDA/SNE/VPO/VPW) must block Heritage Hash Marks (reverse exclusion gap)

Status: directed by Sean 2026-07-11 (same bug class as `287383e` stripe/heritage fix). Implementing same day.

## Diagnosis

Same root cause as `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md` (closed 2026-07-11, `287383e`): grouped `excludes_any` is one-directional (source→target); the workbook convention is explicit reverse groups.

Verified via read-only openpyxl probe of `grandSport_rule_groups`/`grandSport_rule_group_members`:

- `gs_group_sht_excludes_full_length_stripes` (source `opt_sht_001`): targets all 16 stripes + `opt_z15_001` + `opt_pda_001` + `opt_sne_001` + `opt_vpw_001`. No heritage hash-mark targets.
- `gs_group_pda_excludes_stripes_and_z15` (source `opt_pda_001`): targets all 16 stripes + `opt_z15_001`. No heritage hash-mark targets.
- `gs_group_sne_excludes_stripes_and_z15` (source `opt_sne_001`): targets all 16 stripes + `opt_z15_001` + `opt_sht_001` + `opt_vpo_001`. No heritage hash-mark targets.
- `gs_group_vpo_excludes_jake_and_z15` (source `opt_vpo_001`): targets `opt_z15_001`, `opt_pda_001`, `opt_vpw_001`, `opt_sne_001`. No heritage hash-mark targets.
- `gs_group_vpw_excludes_jake_rear_hash_peers` (source `opt_vpw_001`): targets `opt_sht_001`, `opt_vpo_001` only — no `opt_z15_001` and no heritage hash-mark targets (same gap, confirmed per task instruction to check VPW).

Heritage hash marks (`opt_17a_001`, `opt_20a_001`, `opt_55a_001`, `opt_75a_001`, `opt_97a_001`, `opt_dx4_001`, section `sec_gsha_001`) reach Z15 only via `includes` auto-add, suppressed by `shouldSuppressIncludedDefault` (`form-app/app.js:895`) whenever the Stripes section (`sec_stri_001`) already carries a user pick. Repro: Grand Sport step 6, select SNE (Stripes section), then a heritage hash mark (e.g. 17A) — combination completes with no Z15, an invalid order. Same failure mode for SHT/PDA/VPO/VPW sources.

Note: VPO/VPW are a distinct product (`sec_hash_001`, "Jake C8.R Rear Hash Graphic") from the six `sec_gsha_001` Heritage Hash Marks — confirmed via `grandSport_options` option_name lookup. No naming collision risk in the fix.

Change class: workbook data + regeneration + registry publication. Risk: medium (live customer runtime behavior via regenerated data; no code change). Same risk profile as the closed `287383e` fix.

## Fix (workbook-owned, no code changes)

Per task direction: add 5 dedicated reverse-exclusion groups (not extending the 5 existing groups, which serve other purposes — stripes exclusion, Jake-to-Jake conflicts), mirroring the 2026-07-11 `gs_group_<rpo>_excludes_heritage_hash_and_z15` naming and 7-target shape (Z15 + 6 hash marks, Z15 included for symmetry per the established precedent even where already redundant with an existing group):

- `gs_group_sht_excludes_heritage_hash_and_z15` — source `opt_sht_001`
- `gs_group_pda_excludes_heritage_hash_and_z15` — source `opt_pda_001`
- `gs_group_sne_excludes_heritage_hash_and_z15` — source `opt_sne_001`
- `gs_group_vpo_excludes_heritage_hash_and_z15` — source `opt_vpo_001`
- `gs_group_vpw_excludes_heritage_hash_and_z15` — source `opt_vpw_001`

Each: `group_type=excludes_any`, `active=True`, `disabled_reason="<RPO> blocks Grand Sport Heritage Graphics and Heritage Hash Marks."`, notes reference this spec. Members: `opt_z15_001` (10), `opt_17a_001` (20), `opt_20a_001` (30), `opt_55a_001` (40), `opt_75a_001` (50), `opt_97a_001` (60), `opt_dx4_001` (70), all `active=True`.

## Files/sheets expected to change

- `stingray_master.xlsx`: `grandSport_rule_groups` (+5 rows), `grandSport_rule_group_members` (+35 rows). Via `scripts/apply_workbook_ops.py` (dry-run, then `--write`).
- Regenerated: `form-output/` grand-sport artifacts + `form-output/runtime/grand-sport-runtime-contract.json`, `form-app/data.js` (registry publication).
- This spec; fable5loop run receipt + `STATE.md`.

## Source-of-truth decision

Workbook. Runtime `excludes_any` direction handling untouched — same convention as the closed stripe/heritage fix.

## Companion-file impact

- Generated artifacts: regenerated (updated).
- Runtime JS/CSS: inspected, no change.
- Tests: grand-sport node gates + pytest metadata gates re-run; schema gate re-run.
- Docs: none besides this spec.
- Dealer submission: untouched.

## Constraints

No unrelated refactors, no new dependencies, generated files never hand-edited, workbook owns rules, dealer boundaries preserved, no new modules.

## Risks / non-goals

- Risk: over-blocking — mitigated by targeting only Z15 + the 6 heritage hash marks, mirroring the exact shape of the closed fix; verified in browser both directions.
- Non-goal: VPO/VPW's own existing Jake-to-Jake exclusions (SHT↔VPO↔VPW↔SNE↔PDA) — untouched, out of scope.
- Non-goal: generic symmetric `excludes_any` runtime change — workbook convention already directional-explicit.

## Validation plan

1. `apply_workbook_ops.py` dry-run clean → `--write`; verify saved workbook on disk (re-read rows).
2. `validate_workbook_schema.py stingray_master.xlsx`.
3. `generate_form.py --model grand_sport` + `generate_registry.py`; diff review of regenerated artifacts (expect only new rule groups + timestamps).
4. Node gates: `grand-sport-contract-preview`, `grand-sport-draft-data`, `multi-model-runtime-switching`; pytest metadata gates.
5. Browser proof both directions: SNE (or PDA/SHT/VPO/VPW) selected → heritage hash marks + Z15 disabled with reason; heritage hash mark selected first → SNE/PDA/SHT/VPO/VPW disabled (regression, already covered by existing groups); deselect source → hash marks re-enable.
6. Independent verifier per fable loop; run receipt + STATE update.

## Closeout (2026-07-11)

Implemented as specified. 40 ops (5 groups + 35 member rows) applied via `apply_workbook_ops.py --write` (dry-run clean, `--allow-stale` used since the batch was authored fresh against current disk state); schema gate valid; grand-sport node gates 25/25; multi-model-runtime-switching 47/47; pytest metadata 73/73. Browser-proven all 5 sources (SHT, PDA, SNE, VPO, VPW) via DOM/`aria-disabled` inspection — each disables all 6 hash marks + Z15 with correct reason copy; deselect re-enables. Independent verifier subagent (separate context) reproduced all rubric items from scratch — PASS, single cycle. Receipt: `fable5loop/runs/2026-07-11-grand-sport-jake-heritage-hash-reverse-exclusions/`. Residual, out-of-scope: PDA/VPW are not disabled when Z15 or a hash mark is selected first (Z15's own reverse group doesn't target them) — pre-existing, unrelated to this fix.
