# 7-20 Compounded Repair Spec — GSX / ZR1 / ZR1X Options Sheets

Status: IN PROGRESS — Deliverable 4.1 safe bulk set approved 2026-07-20; condensed Checkpoint 1 exception review remains pending. No workbook writes are authorized until the applicable checkpoints are approved.
Supersedes-for-execution: `docs/ingest/options-sheet-quality-remediation-spec.md` (Fable draft) and the recovery plan in `docs/ingest/gpt-auditFindings_7-20.md` (Codex audit). This spec merges the strongest parts of both; the two source docs remain evidence.
Scope: `grand_sport_x_options`, `zr1_options`, `zr1x_options` plus only the referential cascade forced by option-id changes. Promotion, registry, runtime, `form-app`, and dealer surfaces are out of scope.

## 0. Synthesis rationale (what was taken from where)

Taken from the Codex audit (`gpt-auditFindings_7-20.md`):

- **Recovery-by-reuse, not re-review.** GSX shared rows recover from the already-reviewed July 9 plan. Sean reviews only the residual diff, never hundreds of already-reviewed rows. (The original ZR1/ZR1X restore-from-pre-integration idea was invalidated on 2026-07-20 — see §1 correction; ZR1/ZR1X repair forward via §3/§4.1 comparator + `copy_split` proposals.)
- **Sequencing.** Getting the workbook reviewable comes first; the permanent lint project and compiler hardening must not delay it.
- **Explicit GSX partitions**: 203 reviewed shared RPO rows, 10 substantially-correct paint rows, 26 no-RPO standard rows mapped to promoted-model equivalents, 8 fresh RPOs needing real review (N26, PRB, R6P, R9L, R9V, R9W, R9Y, TU7).
- **Temp-workbook apply before any live write.**
- **Rejection of comparator display-order copying** (canonical design says comparator order is not copied) and of stylistic copy rules the reference sheets don't actually prove.

Taken from the Fable draft (`options-sheet-quality-remediation-spec.md` + `Fable-AuditFindings_7-20.md`):

- **Verifier-confirmed root causes with exact locations** (§2 below) — especially the `copy_split` bypass and the fact that the fix routes through existing tested code rather than inventing new copy rules.
- **The id-rename referential cascade** into `*_ovs`, `*_price_rules`, `*_rule_*`, `*_exclusive_*`, `default_selection_rules` — renaming hex ids without this breaks every reference.
- **Executable lint predicates and the permanent gate**, including coverage for unpromoted sheets (the regression escaped because `tests/workbook-visual-copy-standardization.test.mjs` only checks promoted models).
- **Preservation of Sean's in-progress manual edits as reviewer decisions** (5 GSX price fills: AQ9/CF7/CM9/R9W → 0, DTC → 1295) and the GSX row reordering.
- **Probe hygiene**: openpyxl with stale sheet dimensions injects phantom rows; all probes use `read_only=True, data_only=True` and exclude all-None rows.
- **Measurable done-means criteria** and forced-branch compiler regression tests.

Resolved conflicts:

1. *Lint gate first vs. recovery first* → the lint predicates are written first (they are small, executable, and already drafted in the Fable spec §1/§3), but the recovery projection (§4.1) starts in parallel and is not blocked on the pytest gate landing. The gate must be green on the repaired sheets **before the live write** (it grades the repair); it is not a prerequisite for producing the review report.
2. *Display order* → no **silent/automatic** comparator copying — but reviewer-authorized copying is a supported bulk action. The canonical design's "comparator display order is never copied" (`canonical-row-compiler-exception-queue-design.md:442`, `:156`) governs what the compiler does on its own; the same design explicitly allows comparator evidence to prefill review questions (`:11`, `:581`). Per Sean's standing rule (2026-07-20: "scripts set up everything derivable from raw data; form-specific info is presented for review; I authorize copy-from-comparator actions"), the §4.1 report presents comparator ordering as a bulk-acceptable proposal at Checkpoint 1; acceptance is recorded as a typed decision with provenance. Deterministic section-local allocation (increments of 5 or 10 per the z06 pattern) is the fallback where no comparator proposal exists or Sean overrides. GSX rows recovered from the July 9 plan keep their recovered order; existing ZR1/ZR1X rows keep their current real order, and only their three new rows receive proposals. Sean's current GSX row reordering is preserved as a decision.
3. *Copy contract rigidity* → the lint encodes only predicates that hold on the actual reference sheets (z06/grandSport): no `name == description`, no `description == detail_raw` outside allowlist, no newline in `option_name`, no name > 60 chars outside allowlist, no bare-`LPO` names, no hash-derived option ids, no null `display_order` on active rows. Stylistic rules the references don't prove (e.g. Title Case) are dropped.

## 1. Problem — measured

Audit substrate: the **working-copy** `stingray_master.xlsx` (Sean mid-edit; his edits are content to preserve, not drift). Numbers independently reproduced by both audits:

| Metric | z06 (ref) | grandSport | gsx | zr1 | zr1x |
|---|---|---|---|---|---|
| non-empty rows | 244 | 241 | 247 | 216 | 217 |
| `option_name == description` | 0 | 0 | **51** | 1 | 1 |
| `description == detail_raw` | 0 | 0 | **237** | 3 | 3 |
| newline inside `option_name` | 0 | 0 | **32** | 2 | 2 |
| `option_name` > 60 chars | 0 | 1 | **39** | **98** | **98** |
| `display_order` null | 0 | 0 | **237** | 3 | 3 |
| names literally `LPO` | 0 | 0 | **49** | 0 | 0 |
| stub names (≤12 chars) | 4 | 4 | **113** | 3 | 3 |
| `active=False` rows | 5 | 3 | **1** | 1 | 1 |
| priced AND not selectable | 2 | 3 | 0 | **11** | **12** |
| no-RPO rows with 16-hex `opt_std_…` ids | 0 | 0 | **26** | 1 | 1 |

**Corrected 2026-07-20 during deliverable 4.1 (supersedes both audits' claim):** ZR1/ZR1X were never curated. The pre-integration workbook (`281eb14^`) already carries 95 >60-char names per sheet; the integration added exactly 3 rows per sheet (`opt_dtc_001`, `opt_r6p_001`, one hex no-RPO row) and changed zero existing names, descriptions, raw details, or sections (display_order diffs are string→int type coercion only). Verified by direct openpyxl diff of `281eb14^` vs the working copy; all git history and local backups carry the same uncurated copy. There is nothing to restore from history — ZR1/ZR1X copy must be repaired forward (§4.1). The workbook service wrote faithfully throughout.

## 2. Root causes (verifier-confirmed by both audits, all mechanical)

1. `scripts/corvette_form_generator/ingest/wizard/compiler.py:1552` — canonical compiler emits `option_name = description.split(",", 1)[0]`, and sets `description` and `detail_raw` both to the full raw string. The correct tested rules exist in `copy_split.py` (`propose_copy_split`: LPO second-segment, `NEW!+` strip, disclosure-line split, raw-detail preservation) and were consumed only by the legacy decisions/plan path (`plan_builder.py`). The compiler never calls them.
2. `identity.py:181` — no-RPO rows get `opt_std_<sha16>` instead of the z06 short-sequential `opt_NNN` convention.
3. `compiler.py:1547` — `display_order` = existing-else-blank; greenfield GSX had no existing → 237 blanks.
4. `active` is derived from status math, not decided; Sean's per-option instructions had no lane (GSX landed with 1 inactive vs comparator precedent of 3–5).
5. Price semantics carried from source regardless of selectable/standard semantics (11–12 priced standard rows on ZR1/ZR1X; note some priced non-selectable rows are legitimate mandatory charges, e.g. R8E — review lane, not blanket rule).
6. Sean's 45 resolved `choose_section` decisions (run `20260717-091317-470292`, exact `sectionId` payloads) were never reconciled decided-vs-landed — placements are wrong with no trace.
7. Test gap: `tests/workbook-visual-copy-standardization.test.mjs` covers only promoted models, so unpromoted-sheet copy quality had no gate.

## 3. Baseline and preservation rules

- **Freeze the current working-copy workbook as the recovery baseline.** Do not revert wholesale.
- Sean's manual edits are reviewer decisions: the 5 GSX price fills (AQ9/CF7/CM9/R9W → 0, DTC → 1295) and his GSX row reordering. Every projection and changeset diffs against the **live workbook at execution time**, so any further Sean edits made before execution are likewise preserved.
- Recovery sources, in priority order (amended 2026-07-20 — the original ZR1/ZR1X restore-from-`281eb14^` source is invalid; see §1 correction):
  1. Already-reviewed decisions: July 9 plan `form-output/ingest-wizard/20260709-184223-960eb1/apply-plan.json` for GSX shared rows — reused **only where candidate fingerprints still match**; mismatches drop to the review lane.
  2. Exact-RPO promoted-comparator copy proposals (z06 per the approved ZR1/ZR1X comparator mapping; grandSport/z06 for GSX where applicable): curated `option_name`/`description` proposed from the comparator row with the same RPO — presented for Checkpoint 1 bulk accept/override, recorded as typed decisions, never silently applied. `detail_raw` always stays target raw text.
  3. Deterministic derivation (`copy_split`, section-local display-order allocation) where no comparator match exists.
  4. Sean review, only for the residue.
- Probe hygiene: all workbook reads use openpyxl `read_only=True, data_only=True` and exclude rows where every cell is None (stale-dimension phantom rows).

## 4. Deliverables, in order

### 4.1 Recovery projection + residual-diff report (read-only) — the critical path

One script emitting one Markdown/JSON report per model. **Not another ingest run.** Content:

**ZR1 / ZR1X** — amended 2026-07-20: no restore baseline exists (§1 correction — sheets were never curated). Repair forward:
- Copy proposals per row: exact-RPO match against the promoted z06 comparator → propose z06's curated `option_name`/`description`; no match → `copy_split`-derived proposal. Both shown side-by-side with current text at Checkpoint 1 for bulk accept/override; acceptance recorded as typed decisions. `detail_raw` keeps target raw text verbatim.
- Existing rows keep their current (pre-existing, real) `display_order`; the 3 new rows per sheet get section-local allocation or comparator proposal.
- The 1 hex no-RPO id per sheet mapped to a sequential id (cascade per §4.3).
- Priced-standard rows (11–12 each) listed in the §4.1 price lane under Sean's standard-price rule (R8E-class mandatory charges called out as legitimate allowlist candidates).

**GSX** — partitioned:
- 203 shared RPO rows: recover copy/section/order from the July 9 reviewed plan where fingerprints match; retain current `detail_raw` evidence and Sean's price edits.
- 10 paint rows: keep as-is (substantially correct).
- 26 no-RPO standard rows: map to corresponding promoted-model rows; propose short sequential ids and curated copy from the promoted equivalents.
- 8 RPOs absent from the reviewed plan (N26, PRB, R6P, R9L, R9V, R9W, R9Y, TU7): full review lane — several are currently selectable inside the standard-equipment section, so placement/status needs explicit confirmation.

**All three models:**
- Decided-vs-landed section reconciliation: the 45 `choose_section` resolutions from run `20260717-091317-470292` joined to landed `section_id`; every mismatch listed by RPO. (4.1 finding, 2026-07-20: all 45 currently match the landed workbook — the lane stays in the report as a confirmation check, and Sean's remaining placement complaints get captured as new decisions at Checkpoint 1 rather than treated as landing drift.)
- Id repair preview: every hex `opt_std_*` → proposed sequential id, plus the full cross-sheet cascade each rename touches (`*_ovs`, `*_price_rules`, `*_rule_*`, `*_exclusive_*`, `default_selection_rules`).
- `active` review lane: proposed flags with comparator precedent cited; never silently derived.
- Price proposal per **Sean's standard-price rule (stated 2026-07-20, authoritative)**: a standard (non-selectable) row in a section whose `section_master.selection_mode` is `display_only` needs no price (blank); a standard row in a section containing selectable options gets price 0; reviewer-confirmed mandatory charges (R8E-class) are allowlisted exceptions. `selection_mode` is already machine-readable via the compiler's `section_contracts`; the report applies the rule and lists only rows where source data conflicts with it.
- `display_order` proposal, three tiers: (1) recovered order where a reviewed source exists; (2) comparator section ordering presented as a bulk-acceptable proposal — Sean's Checkpoint 1 acceptance records it as a typed decision (reviewer-authorized copy, not silent compiler copy — see §0 conflict 2); (3) deterministic section-local allocation for the remainder.
- Report shows before/after for copy, section, price, active/selectable, order, and id — **residual diff only**; rows whose recovered state equals current state don't appear.

**Checkpoint 1: Sean reviews the report and marks accepts/overrides.** His placement/active/price instructions get recorded once, durably, as decisions.

**Deliverable 4.1 result (2026-07-20):** the read-only reports are in `form-output/ingest-wizard/20260720-options-recovery-projection/`, bound to workbook SHA-256 `4b051a08c53142878039a21103993a4b166bc27b2b5ec5a6e033a52640885578`. All 45 historical section decisions match landed rows (41 GSX, 2 ZR1, 2 ZR1X). Each ZR sheet has 163 exact-Z06 copy proposals eligible for bulk review and zero material-disagreement exclusions; unmatched rows produce 53 ZR1 / 54 ZR1X `copy_split` proposals. Existing ZR display order and all target `detail_raw` values remain unchanged; only DTC, R6P, and the new no-RPO row per sheet receive order proposals. Workbook write authority remains stopped at Checkpoint 1.

**Checkpoint 1 bulk approval (2026-07-20T14:54:02-04:00):** Sean approved the fingerprint-bound safe set: 808 review records covering the 203 reviewed-plan recoveries, 326 exact-RPO comparator-copy proposals, 58 unflagged `copy_split` proposals, 197 authoritative price-rule decisions, 22 comparator-order proposals, and 2 ZR sequential-id repairs. Approval fingerprint: `cf4a92c9c1fef9e4e351879d0f2a5354c3c60c16dca91615ea45c3306cea2ab2`. The remaining 106 review records are condensed into 79 typed decision groups in `checkpoint-1-exception-review.md/.json`; flagged copy splits are excluded from bulk approval. Checkpoint 1 and all workbook-write authority remain open pending those exception decisions.

### 4.2 Lint gate (read-only, permanent) — parallel with 4.1, required before live write

`tests/test_options_sheet_quality.py`: the §0-resolved predicate set plus Sean's standard-price predicate (standard row priced nonzero, or standard row in a selectable-mode section with price None, or standard row in a `display_only` section carrying a price → lint failure unless allowlisted), parameterized over **all** `*_options` sheets (unpromoted included), with a per-model allowlist file for reviewed exceptions (mandatory-charge prices, the two >60-char legacy names on stingray/grandSport, legitimate short paint names, etc.). Runs in the normal pytest gate; required green by any future promotion gate. It grades the §4.3 repair but does not block §4.1 report generation.

### 4.3 One bounded repair ChangeSet

Deterministic script consuming the approved report → one changeset through the existing shared-service path (`editor_ops.apply_batch()` / `scripts/apply_workbook_changeset.py` per current AGENTS §8 direction), touching only the three options sheets plus the exact id cascade from 4.1.

- **Dry-run + temp-workbook apply first**: op counts, before/after per row, workbook fingerprint check; on the temp copy run copy-quality lint (4.2), package validation, schema validation, and reference checks.
- **Checkpoint 2: Sean approves the dry-run/temp proof → live write** via `save_workbook_safely()` with full AGENTS §5 safety (backup, Excel-lock check, readback, package/schema validation, regenerate affected artifacts, diff review).
- Post-apply done check: lint gate green on all three sheets; every `choose_section` decision matches the workbook or carries a recorded Sean override.

### 4.4 Compiler fixes + regression tests

Must land with tests **before any future compiler run against real data**; may proceed in parallel with 4.1–4.3 but never delays them.

1. `compiler.py:1552` routes name/description/detail through `copy_split.propose_copy_split`; raw text lands only in `detail_raw`.
2. `identity.py:181` allocates sequential no-RPO ids against the reserved set.
3. `display_order`: greenfield rows get deterministic section-local allocation; comparator ordering is surfaced only as a typed reviewer-acceptable proposal (never silently copied); blank only with an explicit typed exception.
4. `update` actions never overwrite curated `option_name`/`description` with raw-derived text when the existing value already passes the §4.2 lint.
5. `active`/price get decision lanes instead of silent derivation (typed exceptions where the compiler cannot decide). Price derivation encodes Sean's standard-price rule: replace the current narrow all-statuses-standard zero-fill (`compiler.py:1511–1518`) with section-aware semantics — standard row in a `display_only` section → price blank; standard row in a selectable-mode section → price 0; conflicts and mandatory-charge candidates become typed exceptions, not silent carries.
6. Forced-branch regression tests (per the loop skill's fixture-shadowed-branch failure mode): fixtures forcing the LPO branch, `NEW!` marker, multi-line disclosure name, no-RPO id allocation, and curated-name-preservation update — proving the same input can no longer emit the §1 numbers.

## 5. Explicitly not done

- No replay of the old ChangeSet; no restart of the ingest review; no manual cleanup of all three sheets.
- No `model_master` activation, promotion, registry, runtime contract, or `form-app` change.
- No non-options sheet content cleanup beyond the id cascade.
- No broad copy-standards project beyond the reference-proven predicates.

## 6. Open item for Sean (from both audits)

Commit `281eb14` wrote `stingray_master.xlsx` with no run receipt, against Milestone 3's no-live-write status line. Needs Sean's confirmation on whether that write was separately authorized — independent of this repair.

## 7. Done means

- Lint gate green on gsx/zr1/zr1x with an allowlist Sean has seen: zero name==description, zero description==detail duplication outside allowlist, zero multi-line/oversized names outside allowlist, zero bare-`LPO` names, zero hash-derived option ids, zero null `display_order` on active rows; stub-name count (≤12 chars) at or below the reference-model band (≤6 per sheet, allowlisted).
- ZR1/ZR1X names repaired via Checkpoint-1-approved comparator/`copy_split` proposals; GSX shared rows match the July 9 reviewed decisions or carry recorded overrides; the 8 fresh GSX RPOs and 26 no-RPO mappings carry explicit Sean decisions.
- Sean's manual edits (price fills, reordering) intact in the final workbook.
- Every `choose_section` decision reconciled: matches the workbook or has a recorded override.
- Compiler regression tests prove the §1 numbers cannot recur.
- No promotion/registry/runtime/dealer surface changed.
