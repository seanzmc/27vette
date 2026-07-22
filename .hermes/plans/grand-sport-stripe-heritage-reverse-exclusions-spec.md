# Grand Sport: full-length stripes must block Heritage Hash Marks (reverse exclusion gap)

Status: approved by Sean 2026-07-11 (reported as crucial runtime bug; "fix and push to main"). Implemented same day — see closeout at bottom.

## Diagnosis

**Reported:** Step 6 Stripes — selecting a full-length racing stripe (e.g. DPB) leaves the Grand Sport Heritage Hash Marks section selectable. Hash-mark-first correctly deactivates the racing-stripe choices. Asymmetric.

**Root cause (workbook data gap, not runtime logic):**

- Runtime applies per-row `excludes` rules in both directions (`form-app/app.js:1110` target-side, `:1132` source-side), but grouped `excludes_any` rules only one direction: selected source → candidate target (`excludesAnyReason`, `app.js:1012`). The workbook convention compensates with explicit reverse groups — e.g. every stripe already has `gs_group_<rpo>_excludes_jake_hood_graphics` mirroring the SHT/SNE groups.
- Working direction: hash mark (17A/20A/55A/75A/97A/DX4) auto-adds Z15 via `includes` rules; Z15's group `gs_group_z15_excludes_non_center_stripes` targets all 16 full-length/stinger stripes → stripes deactivate. Evidence: `grandSport_rule_groups` / `grandSport_rule_group_members` sheets; `form-app/data.js` grandSport `ruleGroups`.
- Broken direction: no group or rule anywhere targets the 6 hash-mark options — `grandSport_rule_group_members` contains **zero** rows targeting `opt_17a_001`…`opt_dx4_001`, and the stripes' existing groups target only `opt_sht_001`/`opt_sne_001`. So with DPB selected, hash marks show no disable reason.
- Worse: with DPB user-selected, clicking 17A suppresses the Z15 auto-add (`shouldSuppressIncludedDefault`, `app.js:895` — single-select section already has a user pick), producing an invalid order (DPB + 17A, no Z15).

Change class: workbook data + regeneration + registry publication. Risk: medium (live customer runtime behavior via regenerated data; no code change).

## Fix (workbook-owned, no code changes)

Add 16 reverse exclusion groups, one per full-length/stinger stripe (mirror set of `gs_group_z15_excludes_non_center_stripes` stripe targets):

DPB DPC DPG DPL DPT DSY DSZ DT0 DTH DUB DUE DUK DUW DZU DZV DZX

- `grandSport_rule_groups`: `gs_group_<rpo>_excludes_heritage_hash_and_z15`, `group_type=excludes_any`, `source_id=opt_<rpo>_001`, `disabled_reason="<RPO> blocks Grand Sport Heritage Graphics and Heritage Hash Marks."`, `active=True`, notes reference this spec.
- `grandSport_rule_group_members`: each group targets `opt_z15_001` + the 6 hash marks (`opt_17a_001, opt_20a_001, opt_55a_001, opt_75a_001, opt_97a_001, opt_dx4_001`), display_order 10–70, active=True.

Z15 included as target for full symmetry: with Z15 selected, stripe cards already show blocked (not radio-swap); reverse now matches.

## Files/sheets expected to change

- `stingray_master.xlsx`: `grandSport_rule_groups` (+16 rows), `grandSport_rule_group_members` (+112 rows). Via `scripts/apply_workbook_ops.py` (dry-run, then `--write`).
- Regenerated: `form-output/` grand-sport artifacts + `form-output/runtime/grand-sport-runtime-contract.json`, `form-app/data.js` (registry publication).
- This spec; fable5loop run receipt + `STATE.md`.

## Source-of-truth decision

Workbook. Runtime `excludes_any` direction handling untouched — the repo convention is explicit reverse groups in workbook data (established by the stripe↔SHT/SNE pairs).

## Companion-file impact

- Generated artifacts: regenerated (updated).
- Runtime JS/CSS: inspected, no change.
- Tests: grand-sport node gates re-run; no test contract encodes the buggy behavior (inspected).
- Docs: none besides this spec.
- Dealer submission: untouched.

## Constraints

No unrelated refactors, no new dependencies, generated files never hand-edited, workbook owns rules, dealer boundaries preserved, no new modules.

## Risks / non-goals

- Risk: over-blocking — mitigated by mirroring exactly the Z15 group's stripe set; verified in browser both directions.
- Non-goal: same latent gap exists for Jake graphics (SHT/PDA/SNE/VPO exclude Z15 but not hash marks → same invalid-state path). Out of scope; flagged as follow-up task.
- Non-goal: generic symmetric `excludes_any` runtime change — would alter semantics for all models; workbook convention already directional-explicit.

## Validation plan

1. `apply_workbook_ops.py` dry-run clean → `--write`; verify saved workbook on disk (re-read rows).
2. `validate_workbook_schema.py stingray_master.xlsx`.
3. `generate_form.py --model grand_sport` + `generate_registry.py`; diff review of regenerated artifacts (expect only new rule groups + timestamps).
4. Node gates: `grand-sport-contract-preview`, `grand-sport-draft-data`, `multi-model-runtime-switching`; pytest metadata gates.
5. Browser proof both directions: DPB selected → hash marks + Z15 disabled with reason; hash mark selected → stripes disabled (regression); deselect DPB → hash marks re-enable.
6. Independent verifier per fable loop; run receipt + STATE update.

## Closeout (2026-07-11)

Implemented as specified. 16 groups + 112 member rows applied via `apply_workbook_ops.py --write`; schema gate green; grand-sport + switching gates green; pytest metadata gates green; browser proof captured both directions. Verifier verdict recorded in `fable5loop/runs/2026-07-11-grand-sport-stripe-hash-reverse-exclusions/`. Follow-up (Jake graphics analog) spawned as separate task.
