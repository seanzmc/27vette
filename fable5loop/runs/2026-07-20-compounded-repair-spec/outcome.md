# Outcome — 7-20 Compounded Repair Spec (docs-only)

Task: Sean asked for one master spec merging the strongest parts of the two parallel audits (`docs/ingest/Fable-AuditFindings_7-20.md` + `docs/ingest/options-sheet-quality-remediation-spec.md` vs `docs/ingest/gpt-auditFindings_7-20.md`) into `docs/ingest/7-20_compounded-repair-spec.md`.

## Rubric (defined before writing)

1. Every factual claim (metrics, file:line root causes, run IDs, RPO lists, price-edit values, commit refs) traces to a source doc; referenced artifacts exist on disk / in git.
2. Codex strengths incorporated: recovery-by-reuse (pre-integration ZR1/ZR1X baseline, July 9 plan for GSX shared rows, fingerprint-gated reuse), residual-diff-only review, temp-workbook apply, GSX partitions (203/10/26/8), compiler fix does not delay recovery.
3. Fable strengths incorporated: copy_split-bypass root cause, id-rename referential cascade, permanent lint gate covering unpromoted sheets, Sean's 5 manual price edits preserved as decisions, executable predicates, forced-branch regression tests.
4. Codex's three objections resolved: lint gate does not block report generation; no comparator display-order copying; unproven stylistic copy rules dropped.
5. Boundary safety: no workbook write without checkpoints; promotion/registry/runtime/dealer out of scope; consistent with AGENTS §5/§8.
6. Internally consistent ordering, checkpoints, measurable done-means.

## Result

Spec written: `docs/ingest/7-20_compounded-repair-spec.md`. Independent verifier PASS on all six criteria plus code spot-checks (compiler.py:1547/1552 and identity.py:181 confirmed matching cited behavior). Two verifier minor notes fixed post-verdict: display-order increments restored to "5 or 10 (z06 pattern)"; stub-name band criterion added back to done-means.

No workbook, generated artifact, runtime, registry, promotion, or dealer surface touched. Spec awaits Sean's approval; deliverable 4.1 (recovery projection) is next after approval.

## Post-approval amendment (same day)

Sean approved the spec, then stated two authoritative rules that were under-encoded:

1. Reviewer-authorized comparator copying is legitimate ("scripts set up everything derivable; form-specific presented for review; I authorize copy actions"). The canonical design's "comparator display order is never copied" governs silent compiler behavior only (design doc :442/:156 vs :11/:581 prefill allowance). Spec §0 conflict 2 and §4.1 amended: comparator ordering becomes a bulk-acceptable Checkpoint 1 proposal recorded as a typed decision; deterministic allocation is the fallback.
2. Standard-price rule: standard row in `display_only` section → no price; standard row in selectable-mode section → price 0; mandatory charges allowlisted. Confirmed nowhere in code (compiler.py:1511–1518 zero-fills only on the all-statuses-standard condition, never consults `section_master.selection_mode`, which is already machine-readable via section_contracts). Spec §4.1 price lane, §4.2 lint predicate, and §4.4.5 compiler fix amended to encode it.

## 4.1 mid-flight correction (2026-07-20, Sean's probe + independent confirmation)

Sean paused 4.1: documented ZR1/ZR1X recovery source invalid. Independently confirmed by openpyxl diff of `281eb14^` vs working copy:
- zr1_options 213→216 rows, zr1x_options 214→217; added exactly `opt_dtc_001`, `opt_r6p_001`, one hex no-RPO row per sheet; removed 0.
- Changed existing name/description/detail_raw/section values: 0. display_order "diffs" on 212/214 rows are string→int type coercion with identical values ('20'→20).
- 95 >60-char names per sheet already present pre-integration → sheets were never curated; both audits' clobber claim disproven.
- Sean also reports all 45 choose_section resolutions match the landed workbook (no landing drift).

Approved correction: spec §0/§1/§3/§4.1/§7 amended — ZR1/ZR1X repair forward via exact-RPO promoted z06 comparator copy proposals + copy_split fallback, pending Checkpoint 1; restore source removed; section-reconciliation lane kept as confirmation check. STATE.md gained a superseding verified-fact correction; skill gained "Unverified restore-baseline prescription" failure mode (skill_update decision now: updated).
