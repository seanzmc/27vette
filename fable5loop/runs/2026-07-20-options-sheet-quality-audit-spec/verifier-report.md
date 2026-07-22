# Verifier report

Independent verifier (separate context, read-only, two cycles). Cycle 1: FAIL — three required fixes (phantom-row-corrupted grandSport column, irreproducible gsx unpriced-selectable cell, undefined generic-name metric). Fixes applied; cycle 2 below.

## Verdict
**pass** — all three required fixes are correctly applied and every corrected §1 claim now reproduces exactly on the declared substrate (working-copy workbook, pinned predicates, all-None rows excluded); the 13-vs-8 discrepancy is fully reconciled by enumeration as a real content difference (Sean's in-progress price fills), which the spec now explicitly declares and instructs the repair to preserve.

## Criteria
1. **§1 metrics reproducible — PASS (was FAIL).** Reproduced every corrected cell on the working copy with the spec's own pinned predicates: grandSport 241 rows / 0 null display_order (false footnote deleted, stingray column removed); stub names (`len(option_name.strip()) <= 12`) = 4 / 4 / 113 / 3 / 3, replacing the unverifiable "~64/~40" row; "selectable AND price None" = 6 / 7 / 8 / 2 / 2 — gsx is 8 on the working copy. 13-vs-8 proven by row-level diff: at `a26c797` gsx has 13 such rows (17A 20A 55A 75A 97A AQ9 CF7 CM9 DTC DX4 FED N26 R9W); in the working copy exactly 5 carry manually filled int prices (AQ9/CF7/CM9/R9W → 0, DTC → 1295), leaving 8. All `selectable` cells native bools (156 True / 91 False on gsx). This corrects the cycle-1 overclaim that audited sheets were content-identical to `a26c797` — the identity check had not covered the price column. §6 stub-name criterion uses the ≤6-per-sheet reference band (measured band 4/4/3/3, inside). All previously verified unchanged cells re-confirmed (51/237/32/39/98, max 559/384, 237/3/3 nulls, 49 LPO, inactive counts, 11/12 priced-not-selectable, 26/1/1 hex ids).
2. **Defects trace to cited code — PASS.** `compiler.py:1552-1554` (naive split; description==detail_raw), `compiler.py:1547` (display_order existing-else-blank), `identity.py:181` (`opt_std_<sha16>`); `propose_copy_split` consumed only by plan_builder.py/session.py/decisions.py — zero hits in compiler.py.
3. **Lint gate before repair — PASS.** §4A explicitly "build first"; §1 predicates declared to become §4A lint rules verbatim; §6 done-criteria anchored on the gate.
4. **45 choose_section reconciliation required — PASS.** `form-output/ingest-wizard/20260717-091317-470292/exception-resolutions.json` contains exactly 45 `choose_section` entries with concrete sectionIds (reviewers SeanM/SeanM2); spec §4B.1 + Checkpoint 1 gate the repair on decided-vs-landed reconciliation.
5. **Docs-only — PASS.** Changed surfaces excluding the workbook: STATE.md, the spec, the run directory. Workbook-modified flag affirmatively attributed to Sean's 5 price fills + stale sheet dimensions from an external editor save; no evidence of any session write (all probes openpyxl read_only).

## Evidence inspected
- Spec §1/§6 and audit-metrics.md re-read post-fix.
- Fresh openpyxl probes (read_only=True, data_only=True, all-None rows excluded) on the working-copy workbook: grandSport 241/0; stub≤12 = 4/4/113/3/3; sel-True-price-None = 6/7/8/2/2; selectable cell types all bool.
- Row-level (selectable, price) diff of `grand_sport_x_options` between the `git show a26c797:stingray_master.xlsx` extraction and the working copy: exactly 5 differing rows.
- Cycle-1 evidence for criteria 2–5: code lines, propose_copy_split grep, exception-resolutions.json, git diff --stat excluding workbook.

## Validation Output Inspected
Ran `scripts/validate_fable5_loop.py` in cycle 1 and inspected stored validation-output.txt; only this run's expected pre-verifier failures appeared (pending verdict, independent_context, missing report sections), resolved by this report plus the parent's run.json update. git status re-confirmed: changed surfaces are STATE.md, the spec, the run directory, and the externally edited workbook.

## Required Fixes Before Pass
none

## Durable Lesson Candidates
1. openpyxl `read_only=True` trusts stored sheet dimensions; externally saved workbooks can inject phantom all-None rows — filter them (now encoded in the spec's probe rules).
2. Audit provenance must name the actual substrate; "content-identical to committed" claims require checking every audited column, not just the metric columns — the price-column gap produced the 13-vs-8 confusion.
3. Metrics that feed a lint gate must ship with executable predicates from day one (§1 predicates become §4A rules verbatim).
4. In-progress human edits in a shared artifact are reviewer decisions, not drift — repairs must diff against the live substrate at execution time and preserve them (now §1 policy).

## File Edit Statement
The verifier edited no repository files in either pass; all writes confined to the session scratchpad; all repo access read-only.
