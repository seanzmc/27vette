# Spec: Integrate live-only deltas (GS J57 rule group + app.js requires_any fix) into local structure

Date: 2026-06-10
Branch context: local repo /Users/seandm/Projects/27vette-vis on work/27vette-copy-2026-06-09.
End goal: local organization + live business rules, landing on 27vette main when safe.
Recommended reasoning level if handed to Sean: medium.

## Diagnosis

Two live-only behaviors are missing from local; both have clean, local-native homes.

1. GS J57 requires_any rule group (workbook-owned business rule).
   Live workbook rows (confirmed in diffs/stingray_master.xlsx):
   - grandSport_rule_groups:
     group_id=gs_group_j57_z52_requirement, group_type=requires_any,
     source_id=opt_j57_001, disabled_reason="Requires FEB Z52 Sport
     Performance Package or FEY Z52 Track Performance Package.",
     active=True, notes="J57 is selectable with FEB, or included by FEY."
   - grandSport_rule_group_members:
     (gs_group_j57_z52_requirement, opt_feb_001, 1, True)
     (gs_group_j57_z52_requirement, opt_fey_001, 2, True)
   Local workbook dropped these 3 rows during the reorg. Local headers for both
   sheets are unchanged, so the rows port verbatim. This is data-only; the
   generator already understands requires_any groups.

2. app.js requires_any predictive preview (generic runtime behavior).
   Live requiresAnyReason() simulates the candidate selection:
   builds candidateSelectedIds = selectedIds + choice.option_id +
   computeAutoAdded([choice.option_id]).keys(), then evaluates requires_any
   targets against the simulated set. computeAutoAdded(extraIds = []) gains an
   extraIds seed param. Local's version only explains violations on already-
   selected options. Live is a strict superset, generic (no model/RPO
   hardcoding), and is the version production users have today. Confined to
   two functions; the rest of app.js is identical between sides.

Risk level: low-medium. Workbook write + regen of GS artifacts + small runtime
edit. No schema changes, no new dependencies, no refactor.

Change type: mixed (workbook data + runtime JS), but each piece is owned by its
canonical layer — rule in workbook, preview behavior in runtime.

## Exact changes

A. Workbook (stingray_master.xlsx, local):
   - Append 1 row to grandSport_rule_groups and 2 rows to
     grandSport_rule_group_members with the exact live values above.
   - Write via a short openpyxl script using save_workbook_safely()
     (scripts/corvette_form_generator/workbook.py). Excel closed, no
     ~$stingray_master.xlsx lock. Verify rows on disk after save.
   - One-pass apply script is throwaway: delete after browser verification
     (user preference).

B. Runtime (form-app/app.js, local):
   - Replace local requiresAnyReason() with live's candidate-simulation
     version (verbatim from diffs/form-app/app.js lines ~834-848).
   - Change computeAutoAdded() signature to computeAutoAdded(extraIds = [])
     and seed selectedIds from extraIds (verbatim live lines ~874-880).
   - No other app.js edits.

C. Regenerate (local pipeline):
   - .venv/bin/python scripts/generate_form.py --model grand_sport
   - .venv/bin/python scripts/build_rule_sources.py --model grand_sport
     (only if rule-source sheets are part of the GS regen contract — verify
     whether generate_form covers it; otherwise skip and note)
   - Expected artifact deltas: grand-sport draft/preview/rule-audit/runtime-
     contract show 27 ruleGroups / 176 members / 4 groupedRequirementPairs
     (matching live counts), nothing else beyond timestamps.
   - form-app/data.js: grandSport.ruleGroups gains the one group; review with
     node scripts/compare-generated-contracts.mjs against pre-change JSON to
     confirm the delta is only the J57 group.

## What this spec does NOT cover (named, deferred decisions)

- review_flag / price_semantic / lifecycle taxonomy conflict
  (schema_validation.py + workbook columns). Separate pass; required before
  the final merge to live main.
- R6X manual interior-includes synthesis verification (live Python-synthesized
  includes vs local workbook rule_mapping coverage). Separate verification
  pass; required before merge.
- Promotion artifact_path migration mechanics on the live repo (workbook rows
  + runtime-contract artifacts must ship with the code).
- ZR1/ZR1X anything.

## Constraints

- No refactor, no new dependencies, no visual changes beyond the predictive
  disabled-reason text appearing on unselected options (that is the fix).
- Dealer submission endpoint/payload/Turnstile untouched.
- No hardcoded model/RPO logic: the rule lands as workbook rows; the JS change
  is generic group evaluation.
- Do not edit generated form_* sheets or data.js by hand.

## Risks

- computeAutoAdded(extraIds) is called in a simulation context per render of
  unselected choices; live already ships this, so perf/behavior risk is
  demonstrated-low.
- Regen could surface unrelated workbook diffs if local sheets drifted since
  the 06-10 regen; mitigated by contract compare before/after.
- Workbook write risk mitigated by save_workbook_safely() + on-disk
  verification + backups/ convention.

## Validation plan

1. Pre-change snapshot: copy form-output/inspection/grand-sport-*.json and
   form-app/data.js aside for compare.
2. Apply A, verify rows on disk (openpyxl read-back).
3. .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
4. Apply B; regen per C; contract-compare.
5. Gates:
   node --test tests/grand-sport-contract-preview.test.mjs
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/grand-sport-rule-audit.test.mjs
   node --test tests/audit-parser-metadata-loaders.test.mjs
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
6. Browser smoke (cd form-app && ../.venv/bin/python -m http.server 8000):
   Grand Sport, no FEB/FEY selected -> J57 shows disabled with "Requires FEB
   Z52 Sport Performance Package or FEY Z52 Track Performance Package.";
   select FEB -> J57 selectable; select FEY -> J57 included path intact.
   Also verify T0F preview (existing gs_group_t0f_z52_requirement) still
   renders predictively with the new app.js — this exercises the JS fix.
7. Z06 regression check (REQUIRED — this is the bug the live fix addresses,
   per bug-report-6-10-2026.md / live commit c49e4d7 "fix: improve logic for
   requiresAnyReason and computeAutoAdded functions"):
   The pre-fix requiresAnyReason wrongly disabled Z06 options whose
   requires_any constraint is satisfied by the option's OWN prospective
   auto-adds (the candidate-simulation via computeAutoAdded([choice.option_id])
   is what fixes this). Verify in browser on Z06:
   - Z07 is selectable by default (its gate is satisfied by its auto-added
     J57 cascade), and selecting it auto-adds J57 at $0 non-removable.
   - Carbon wheel packages PDB/PDD/PDF are available once J57 is
     selected/auto-added, and carbon-fiber wheel choices ROY/ROZ/STZ are
     enabled — none of them stuck in a disabled "requires" state while
     unselected.
   Test gates that lock this behavior:
   node --test tests/z06-performance-package-interactions.test.mjs
   node --test tests/z06-runtime-rule-corrections.test.mjs
   If local app.js currently exhibits the broken behavior (it has the
   pre-fix logic), confirm the breakage BEFORE the port and the fix AFTER —
   a true RED->GREEN check.
8. Delete the one-pass workbook apply script after browser verification.

## Path to 27vette main (sequencing, not in this pass)

1. This pass (J57 rows + app.js fix) on the local copy.
2. Taxonomy decision pass (review_flag/price_semantic/lifecycle).
3. R6X includes-coverage verification pass.
4. Merge pass: bring local tree onto a branch of /Users/seandm/Projects/27vette
   (live repo), as a curated commit series — local structure wholesale, live
   deltas already absorbed by passes 1-3. Live workbook is replaced by local
   workbook (which by then contains every live business rule). Promotion rows
   already point at runtime-contract artifacts in local; regenerate all three
   models in the live repo and run the full AGENTS.md suite there.
5. PR/merge to 27vette main only after full suite + browser smoke on the live
   repo checkout. Note: local main of /Users/seandm/Projects/27vette was
   previously repaired ahead-1 of origin/main; reconcile that before merging.

## Approval question

Approve pass 1 (A+B+C with validation above) on work/27vette-copy-2026-06-09?
Taxonomy and R6X passes will be specced separately after this lands.
