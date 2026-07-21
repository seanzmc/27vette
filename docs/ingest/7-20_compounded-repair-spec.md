# 7-20 Compounded Repair Spec — GSX / ZR1 / ZR1X Options Sheets

Status: IN PROGRESS — Deliverables 4.1–4.3 and Checkpoint 2 are complete as of 2026-07-20. The exact approved repair is applied and validated in the canonical workbook; §4.4 compiler prevention remains next. No activation, promotion, registry publication, runtime deployment, or dealer change has occurred.
Supersedes-for-execution: `docs/ingest/options-sheet-quality-remediation-spec.md` (Fable draft) and the recovery plan in `docs/ingest/gpt-auditFindings_7-20.md` (Codex audit). This spec merges the strongest parts of both; the two source docs remain evidence.
Scope: `grand_sport_x_options`, `zr1_options`, `zr1x_options` plus only the referential cascade forced by option-id changes. Promotion, registry, runtime, `form-app`, and dealer surfaces are out of scope.

## 0. Synthesis rationale (what was taken from where)

Taken from the Codex audit (`gpt-auditFindings_7-20.md`):

- **Recovery-by-reuse, not re-review.** GSX shared rows recover from the already-reviewed July 9 plan. Sean reviews only the residual diff, never hundreds of already-reviewed rows. (The original ZR1/ZR1X restore-from-pre-integration idea was invalidated on 2026-07-20 — see §1 correction; ZR1/ZR1X repair forward via §3/§4.1 comparator reuse plus identifying-copy derivation.)
- **Sequencing.** Getting the workbook reviewable comes first; the permanent lint project and compiler hardening must not delay it.
- **Explicit GSX partitions**: 203 reviewed shared RPO rows, 10 substantially-correct paint rows, 26 no-RPO standard rows mapped to z06 equivalents, and 8 fresh RPOs now covered by Sean's cross-target delete decision (N26, PRB, R6P, R9L, R9V, R9W, R9Y, TU7).
- **Temp-workbook apply before any live write.**
- **Rejection of comparator display-order copying** (canonical design says comparator order is not copied) and of stylistic copy rules the reference sheets don't actually prove.

Taken from the Fable draft (`options-sheet-quality-remediation-spec.md` + `Fable-AuditFindings_7-20.md`):

- **Verifier-confirmed root causes with exact locations** (§2 below) — especially the compiler's bypass of the existing split path. Deliverable 4.1 separately uses reference-proven identifying-copy derivation because the generic split path is not sufficient for customer-facing names.
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
  3. Deterministic identifying-copy derivation and section-local display-order allocation where no comparator match exists. Copy derivation must keep the distinguishing finish/color/design/specification in `option_name`, move only ancillary information to `description`, avoid repetition, and fail closed to a curated-copy review rather than emitting a generic one-word name.
  4. Sean review, only for the residue.
- Probe hygiene: all workbook reads use openpyxl `read_only=True, data_only=True` and exclude rows where every cell is None (stale-dimension phantom rows).

## 4. Deliverables, in order

### 4.1 Recovery projection + residual-diff report (read-only) — the critical path

One script emitting one Markdown/JSON report per model. **Not another ingest run.** Content:

**ZR1 / ZR1X** — amended 2026-07-20: no restore baseline exists (§1 correction — sheets were never curated). Repair forward:
- Target applicability is evaluated before copy review: when every status cell for the target model's four variants is `--`, that target option row and its target-owned references are deletion work, not copy/placement review. The sibling model is evaluated independently from its own four columns even though the raw sheet is shared; no duplicated raw rows are required.
- Copy proposals per row: exact-RPO match against the promoted z06 comparator → propose z06's curated `option_name`/`description`; no match → identifying-copy proposal that retains the unique equipment identifier in the name and ancillary non-repeating information in the description. The latter remains in Checkpoint 1 for accept/override and is never bulk-approved merely because a split was mechanically possible. `detail_raw` keeps target raw text verbatim.
- Blank-RPO rows use a one-to-one semantic match against **z06 only** and copy z06's exact curated `option_name`/`description`, even though target option IDs differ. These deterministic mappings are not review questions; unmatched or colliding mappings fail closed.
- Sean's recorded deletion of N26, PRB, R6P, R9L, R9V, R9W, R9Y, and TU7 applies across all three target models. ZR1/ZR1X therefore also delete N26, R6P, and TU7 (the only members of that set present there), plus their model-owned references; absent members require no synthetic row or review.
- Existing rows keep their current (pre-existing, real) `display_order`; surviving new rows get section-local allocation or comparator proposal, while deleted rows receive no order.
- The 1 hex no-RPO id per sheet mapped to a sequential id (cascade per §4.3).
- Priced-standard rows (11–12 each) listed in the §4.1 price lane under Sean's standard-price rule (R8E-class mandatory charges called out as legitimate allowlist candidates).

**GSX** — partitioned:
- 203 shared RPO rows: recover copy/section/order from the July 9 reviewed plan where fingerprints match; retain current `detail_raw` evidence and Sean's price edits.
- 10 paint rows: keep as-is (substantially correct).
- 26 no-RPO standard rows: one-to-one map to z06 blank-RPO rows; copy exact z06 names/descriptions and propose short sequential ids without a copy-review lane.
- 8 RPOs absent from the reviewed plan (N26, PRB, R6P, R9L, R9V, R9W, R9Y, TU7): Sean's recorded decision is deletion from GSX and from either ZR target wherever present, including model-owned references.

**All three models:**
- Decided-vs-landed section reconciliation: the 45 `choose_section` resolutions from run `20260717-091317-470292` joined to landed `section_id`; every mismatch listed by RPO. (4.1 finding, 2026-07-20: all 45 currently match the landed workbook — the lane stays in the report as a confirmation check, and Sean's remaining placement complaints get captured as new decisions at Checkpoint 1 rather than treated as landing drift.)
- Id repair preview: every hex `opt_std_*` → proposed sequential id, plus the full cross-sheet cascade each rename touches (`*_ovs`, `*_price_rules`, `*_rule_*`, `*_exclusive_*`, `default_selection_rules`).
- `active` review lane: proposed flags with comparator precedent cited; never silently derived.
- Price proposal per **Sean's standard-price rule (stated 2026-07-20, authoritative)**: a standard (non-selectable) row in a section whose `section_master.selection_mode` is `display_only` needs no price (blank); a standard row in a section containing selectable options gets price 0; reviewer-confirmed mandatory charges (R8E-class) are allowlisted exceptions. `selection_mode` is already machine-readable via the compiler's `section_contracts`; the report applies the rule and lists only rows where source data conflicts with it.
- `display_order` proposal, three tiers: (1) recovered order where a reviewed source exists; (2) comparator section ordering presented as a bulk-acceptable proposal — Sean's Checkpoint 1 acceptance records it as a typed decision (reviewer-authorized copy, not silent compiler copy — see §0 conflict 2); (3) deterministic section-local allocation for the remainder.
- Report shows before/after for copy, section, price, active/selectable, order, and id — **residual diff only**; rows whose recovered state equals current state don't appear.

**Checkpoint 1: Sean reviews the report and marks accepts/overrides.** His placement/active/price instructions get recorded once, durably, as decisions.

**Deliverable 4.1 result (2026-07-20):** the read-only reports are in `form-output/ingest-wizard/20260720-options-recovery-projection/`, bound to workbook SHA-256 `4b051a08c53142878039a21103993a4b166bc27b2b5ec5a6e033a52640885578`. All 45 historical section decisions match landed rows (41 GSX, 2 ZR1, 2 ZR1X). Target-scoped raw evidence removes five false review rows before copy repair: FEH/FEZ from ZR1 and FE8/FEJ/SIG from ZR1X, including 20 OVS rows and three target-owned rule mappings; the applicable sibling-model rows and same-id references outside the target are preserved. The recorded cross-target delete set additionally removes N26, R6P, and TU7 from both ZR sheets and projects their model-owned reference cascades. All 26 blank-RPO rows in each target model copy exact z06 names/descriptions with zero no-RPO review questions. Existing ZR display order and every surviving target `detail_raw` value remain unchanged. Workbook write authority remains stopped at Checkpoint 1.

**Checkpoint 1 bulk approval (rebound 2026-07-20T17:36:46-04:00 after copy/deletion correction):** Sean's approved safe set binds 742 review records: 203 reviewed-plan recoveries, 325 exact-RPO comparator-copy proposals, 190 authoritative price-rule decisions, 22 comparator-order proposals, and 2 ZR sequential-id repairs. No derived identifying-copy proposal is bulk-approved. Approval fingerprint: `ae94629935489b680848662b3514e908ddedc9424cb23761f9daf18abfe6da1a`.

**Checkpoint 1 complete (final amendment 2026-07-20):** all 54 exception groups / 74 exception review records now carry typed decisions; pending groups and reviews are both zero. Sean deleted 36S, 37S, 38S, and N2Z from both ZR option sheets with their owned references; approved CFC, DTB, ETV, FE8 through MLP, SB9, SOF through SU1, and both TOM proposals; and approved DTC copy with price 1295 in both models. ZTK carries model-scoped copy: ZR1 references FEJ plus the J59 10-piston-front/6-piston-rear carbon-ceramic brakes, while ZR1X references FEZ and omits FEJ. Eighteen explicit overrides blank the standard-equipment prices for UQT, CFV, DY0, WUB, C2Z, B6P, ZZ3, D3V, and SL9 in both ZR sheets; promoted-model selectable-option prices remain untouched. Nine deterministic display-order collision repairs were recorded under the already-approved order rule. Fifty GSX residual reviewed-plan rows now carry exact promoted-Grand-Sport copy overrides, and Sean approved the five remaining identifying-copy exceptions (SWP, T0E, FE5, HP1, and MLG) exactly as shown in the condensed packet. The final decision artifact contains 82 typed bulk overrides with fingerprint `2b5efc890c7478169128cf15bbffe168c13ccf162733ac6bfe4515047ed00521`. No workbook mutation has occurred.

### 4.2 Lint gate (read-only, permanent) — parallel with 4.1, required before live write

`tests/test_options_sheet_quality.py`: the §0-resolved predicate set plus Sean's standard-price predicate (standard row priced nonzero, or standard row in a selectable-mode section with price None, or standard row in a `display_only` section carrying a price → lint failure unless allowlisted), parameterized over **all** configured source option sheets (unpromoted included), with a per-model allowlist file for exact reviewed exceptions (mandatory-charge prices, the three actual >60-character promoted-reference names, package-controlled/automatic reference rows, and Sean's 18 explicit blank-price ZR exceptions). Runs in the normal pytest gate; required green by any future promotion gate. It grades the §4.3 repair but does not block §4.1 report generation.

**Deliverable 4.2 result (2026-07-20):** `scripts/corvette_form_generator/options_sheet_quality.py` provides a read-only callable and CLI with machine-readable JSON output; `tests/test_options_sheet_quality.py` proves every predicate, inactive-sheet discovery, fail-closed exit status, stub-count limit, and exact-value allowlist binding. `tests/fixtures/options-sheet-quality-allowlist.json` contains 32 exact row/check/value exceptions with reasons; changed values are not suppressed. The promoted Stingray/Grand Sport/Z06 references have zero unallowlisted findings. The unrepaired canonical targets correctly fail with 1,080 findings (GSX 728, ZR1 175, ZR1X 177); the §4.3 repaired temporary workbook passes with zero findings and all 16 quality tests green. No canonical workbook mutation occurred.

### 4.3 One bounded repair ChangeSet

Deterministic script consuming the approved report → one changeset through the existing shared-service path (`editor_ops.apply_batch()` / `scripts/apply_workbook_changeset.py` per current AGENTS §8 direction), touching only the three options sheets plus the exact owned-reference cascades forced by approved option deletes and option-id repairs from 4.1.

- **Dry-run + temp-workbook apply first**: op counts, before/after per row, workbook fingerprint check; on the temp copy run copy-quality lint (4.2), package validation, schema validation, and reference checks.
- **Checkpoint 2: Sean approves the dry-run/temp proof → live write** via `save_workbook_safely()` with full AGENTS §5 safety (backup, Excel-lock check, readback, package/schema validation, regenerate affected artifacts, diff review).
- Post-apply done check: lint gate green on all three sheets; every `choose_section` decision matches the workbook or carries a recorded Sean override.

**Deliverable 4.3 temporary-proof result (2026-07-20):** `options_recovery_changeset.py` emitted immutable ChangeSet `6c156ef7b4216d3dd85b48f7` (semantic fingerprint `6c156ef7b4216d3dd85b48f716028240c3c4e9e37e20d5f5ca2fc1cbb4b4bd58`) with 1,128 row operations: 192 adds, 355 deletes, and 581 updates across the three option sheets and seven exact owned-reference sheets. The shared-service preview is `validated`, covers 1,128/1,128 raw operations, and has no blocking warnings. A disposable apply saved successfully; package validation, schema validation, and the option-sheet quality gate all report zero issues, 16 quality tests and 147 related tests pass, and the ten sheets with actual cell changes exactly equal the ChangeSet sheet set. Final option-row counts are GSX 239, ZR1 207, and ZR1X 207; all requested target deletes, copy decisions, prices, ZTK model-specific copy, id repairs, and 45/45 section reconciliations match. Proof: `form-output/ingest-wizard/20260720-options-recovery-projection/checkpoint-2-temp-proof.{json,md}`. The canonical workbook remains at SHA-256 `4b051a08c53142878039a21103993a4b166bc27b2b5ec5a6e033a52640885578` and mtimeNs `1784557974349071046`. Checkpoint 2 is ready; no live workbook write, generation, publication, promotion, runtime deployment, or dealer change has occurred.

**Checkpoint 2 live-write result (2026-07-20):** Sean approved the exact bound ChangeSet, and the guarded service applied and read back all 1,128 operations before reporting `saved`. The recoverable backup is `backups/stingray_master-20260720-221409.xlsx`, whose SHA-256 `4b051a08c53142878039a21103993a4b166bc27b2b5ec5a6e033a52640885578` exactly matches the pre-write workbook; the saved canonical workbook SHA-256 is `31764a718a29f1705961674d97de821e1474f97a4234209fef3a4fe2bce8ece3`. Package validation, schema validation, and the option-sheet quality gate pass with zero issues; 147 related tests pass. The ten sheets with actual cell changes exactly match the ChangeSet sheet set, final option-row counts remain GSX 239 / ZR1 207 / ZR1X 207, all requested deletions and five final copy approvals match, and no legacy `opt_std_*` ids remain. Live proof: `form-output/ingest-wizard/20260720-options-recovery-projection/checkpoint-2-live-proof.{json,md}`. Generated artifacts and `form-app/data.js` remain unchanged because the models are still inactive and the canonical generator rejects inactive targets; activation/promotion was not authorized by Checkpoint 2.

### 4.4 Compiler fixes + regression tests

**Specification status: IMPLEMENTED AND VERIFIED (2026-07-21).** This recurrence-prevention deliverable landed with focused and full ingest regression coverage before a fresh real-source compiler characterization. It changes compiler mechanics and exception handling only; it does not introduce model-specific business rules, activate a model, write the workbook, or publish runtime data.

#### 4.4.1 Authoritative contract

The compiler is governed by five rules. They are intentionally ordered and are the complete product contract for this deliverable:

1. **Delete target-specific all-`--` rows first.** Resolve applicability before identity, copy, placement, behavior, or price. If every status cell for the selected target is `--`, delete that target's unique option occurrence and exact target-owned references without creating copy or placement review. Shared source sheets do not merge model scope: ZR1 and ZR1X are evaluated independently, and sibling-model rows/references remain intact. Ambiguous identity or ownership blocks the deletion rather than broadening it.
2. **Preserve curated copy; propose only what changed or is new.** Apply these exact rules:
   - Keep an existing valid `option_name` and `description` when source `detail_raw` is unchanged. For new or source-changed rows, create the best deterministic proposal: exact comparator copy when there is one unambiguous match, otherwise `copy_split.propose_copy_split()`. Preserve target source text verbatim in `detail_raw`.
   - Measure comparator agreement with the existing `_comparator_copy_comparison()` semantics in `scripts/corvette_form_generator/ingest/options_recovery_projection.py` (extracted to a shared helper if needed): tokenize the complete target raw text and comparator `option_name`, remove `COPY_COMPARISON_STOPWORDS`, and flag a material conflict when matched comparator-name-token coverage is **less than `0.60`**.
   - Every non-empty review flag emitted by `propose_copy_split()` is individually blocking, whether or not §4.2 also detects it. The current blocking set is `one_word_name`, `no_sentence_break`, `name_over_60_chars`, `unmatched_footnote_marker`, and `all_text_matched_disclosure`; queue-level `duplicate_proposed_name` is blocking too. Future unknown split flags fail closed rather than becoming automatic. A normalized one-word generic proposal such as `Wheels`, `Calipers`, `Seats`, `Suspension`, or `Trim` is also blocking even if an older helper path failed to attach `one_word_name`.
   - Only proposals with no ambiguity, no material comparator conflict, no split/queue review flag, and no §4.2 copy-quality flag may proceed automatically. Any named blocker requires individual copy review and is excluded from bulk acceptance.
3. **IDs and order are mechanical.** Preserve uniquely matched existing ids and valid existing section-local order. Allocate new blank-RPO ids deterministically from the lowest unused target-local `opt_NNN`; never emit `opt_std_<hash>`. Resolve section before order. For each new row, section move, missing order, or collision, assign the next unused positive multiple of `10` strictly above that target section's current maximum; reserve it immediately in the compile-local section set before processing the next row. Sort candidates by semantic signature before allocation so source iteration order cannot change the result, and never renumber retained target rows to make room. No row-by-row id or order decision is required; review is limited to ambiguous identity, unresolved section placement, or an actual placement conflict that cannot be resolved without changing curated placement.
4. **Behavior and price follow workbook rules.** Apply these exact rules:
   - A row is applicable only when all target statuses are resolved and at least one is `available` or `standard`; Rule 1 has already removed the all-unavailable case. “Exact target default evidence” means one active target-owned `default_selection_rules` row whose `target_option_id` is this option, whose `display_behavior` is `default_selected`, and whose condition and scopes are valid for the selected target. Comparator-only default evidence is not authority.
   - Preserve existing `(active=False, selectable=False)` unless exact target default evidence conflicts by requiring that option to participate in a `single_select_req` section. Preserve existing `(active=True, selectable=False)` when the row is applicable and its section is resolved. Preserve existing `(active=True, selectable=True)` only when the section mode is not `display_only` and either at least one target status is `available`, or the row is `standard` in `single_select_req` with exact target default evidence. `(active=False, selectable=True)` is never compatible. Target source status by itself never changes an existing `active=False` or `selectable=False` to `True`; an incompatible pair creates one behavior conflict and remains unchanged until resolved.
   - For a new applicable row with a resolved section, derive `active=True`. Derive `selectable=False` in `display_only`; derive `selectable=True` when any target status is `available` in `single_select_req`, `single_select_opt`, or `multi_select_opt`; derive `selectable=False` for ordinary all-`standard` rows. An all-`standard` row in `single_select_req` becomes selectable only with exact target default evidence; missing or ambiguous required-choice evidence blocks instead of guessing.
   - Derive standard-equipment price only after section and behavior: blank in `display_only`; `0` in selectable-mode sections, including a supported required single-select default. Ordinary available options retain the existing exact/conditional price path. No row-by-row behavior or price decision is required; review only the conflicts defined here or a mandatory-charge candidate. Never hardcode an RPO-specific exception.
5. **The complete projected sheet must pass before emission.** Evaluate the full desired target sheet—retained rows plus projected changes—with the §4.2 quality predicates after all deterministic work and accepted resolutions. Any unallowlisted issue or unresolved blocker keeps `compileReady=false`; `changeset_emitter.py` must refuse the ChangeSet. The compiler authority dependencies must include the repo-relative allowlist path `tests/fixtures/options-sheet-quality-allowlist.json` and that file's SHA-256. Changing either the path or content makes existing compile artifacts, subjects, and resolutions stale. Allowlist entries remain exact model/sheet/option/check/value bindings and cannot be created or widened by the compiler.

These rules remove the prior requirement that every new row receive separate copy, behavior, and order decisions. Review is exception-driven: deterministic, non-conflicting work is automatic; only the conflicts named above reach an individual reviewer.

Every conflict that reaches review must carry and display, without truncation, the current `option_name` and `description`, proposed `option_name` and `description`, complete target `detail_raw`, comparator copy and comparison evidence (or an explicit `not_available` value when no comparator exists), plus the exact behavior/placement/price evidence relevant to that conflict. A tooltip or truncated table cell does not satisfy this contract.

The compiler policy version must be bumped so prior artifacts/resolutions cannot be silently reused under this contract.

#### 4.4.2 Implementation checklist (non-authoritative)

This checklist preserves the useful repo-traced file and test detail without expanding the five-rule contract. Reconfirm each touch point while implementing and omit any file that does not need to change.

**Compiler and quality path**

- `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py`: bump `COMPILER_POLICY_VERSION`.
- `scripts/corvette_form_generator/ingest/wizard/parser.py`: retain the exact source Description text for `detail_raw` and evidence/fingerprints while preserving the cleaned working value used for matching/parsing.
- `scripts/corvette_form_generator/ingest/wizard/copy_split.py`: reuse the full-target comparator material-comparison and split helpers; preserve existing `LPO`, `NEW!`, disclosure, and raw-detail behavior.
- `scripts/corvette_form_generator/ingest/wizard/identity.py`: deterministic target-local `opt_NNN` reservation/allocation with explicit ambiguity, collision, and exhaustion failure.
- `scripts/corvette_form_generator/ingest/wizard/compiler.py`: apply the five rules in order; remove the first-comma/full-raw copy assignment and pre-section all-standard zero-fill.
- `scripts/corvette_form_generator/options_sheet_quality.py`: expose a pure full-row-set evaluator shared by workbook lint and compiler while keeping the CLI/report schema stable; pass the exact allowlist path and SHA into compiler authority dependencies.
- `scripts/corvette_form_generator/ingest/wizard/changeset_emitter.py`: preserve the existing ready/empty-blocker fail-closed boundary.

**Exception and review path**

- Reuse the existing exception schema where possible. Add or adjust typed reasons in `scripts/corvette_form_generator/ingest/wizard/exceptions.py` and their consumers in `scripts/corvette_form_generator/ingest/wizard/session.py` only for actual ambiguous/conflicting copy, identity/placement, behavior/price, or quality blockers.
- Update `visualizer/ingest-wizard/wizard.js` and `visualizer/ingest-wizard/wizard.css` to satisfy the mandatory untruncated evidence contract in §4.4.1. The browser must not create per-row review cards for deterministic ids, orders, behavior, prices, or unflagged copy proposals.
- A stale resolution or a resolution that still fails the projected-sheet gate reopens/remains blocking; there is no generic “accept quality issue” action.

**Regression proof**

- Add focused coverage in `tests/test_ingest_wizard_parser.py`, `tests/test_ingest_wizard_copy_split.py`, `tests/test_ingest_wizard_identity.py`, `tests/test_ingest_wizard_exceptions.py`, `tests/test_ingest_wizard_canonical_rows.py`, `tests/test_ingest_wizard_canonical_compiler.py`, `tests/test_ingest_wizard_exception_flow.py`, `tests/test_ingest_wizard_changeset.py`, `tests/test_ingest_wizard_ui_milestone2.py`, `tests/test_ingest_wizard_server.py`, and `tests/test_options_sheet_quality.py` as each surface requires.
- Forced branches cover: shared-sheet target-specific all-`--` deletion; curated-copy preservation; comparator coverage exactly at `0.60` and immediately below it; every current split flag (`one_word_name`, `no_sentence_break`, `name_over_60_chars`, `unmatched_footnote_marker`, `all_text_matched_disclosure`); queue-level `duplicate_proposed_name`; an unflagged generic one-word proposal from an older helper path; deterministic blank-RPO ids; multiple same-section allocations proving immediate order reservation; preserved inactive curated behavior despite available source status; each new-row behavior branch; display-only/selectable-section standard prices; mandatory-charge review; allowlist-authority staleness; and full-sheet quality refusal.
- Assert deterministic work creates no individual review subject. Assert every split/queue flag and every generic one-word proposal creates an individual blocker and cannot enter an automatic or bulk-accept path. Assert source status never silently reactivates or makes an existing row selectable, invalid existing combinations block unchanged, and only ambiguity/material conflict/copy-review/quality flags and mandatory charges block. Changing the bound allowlist path or bytes must stale the prior artifact and resolutions. A second identical compile with unchanged authority dependencies must produce identical row values and semantic fingerprints.
- Assert no ready row has invalid copy, `opt_std_<hash>`, blank/colliding active-row order, invalid standard price, or altered non-target ownership; exact source text remains in `detail_raw`.

#### 4.4.3 Validation and stop conditions

Run, in order:

```sh
PYTHONPATH=scripts:tests .venv/bin/python -m pytest \
  tests/test_ingest_wizard_parser.py \
  tests/test_ingest_wizard_copy_split.py \
  tests/test_ingest_wizard_identity.py \
  tests/test_ingest_wizard_exceptions.py \
  tests/test_ingest_wizard_canonical_rows.py \
  tests/test_ingest_wizard_canonical_compiler.py \
  tests/test_ingest_wizard_exception_flow.py \
  tests/test_ingest_wizard_changeset.py \
  tests/test_ingest_wizard_ui_milestone2.py \
  tests/test_ingest_wizard_server.py \
  tests/test_options_sheet_quality.py -q

PYTHONPATH=scripts:tests .venv/bin/python -m pytest tests/test_ingest_wizard*.py -q

PYTHONPATH=scripts .venv/bin/python -m corvette_form_generator.options_sheet_quality \
  --workbook stingray_master.xlsx \
  --allowlist tests/fixtures/options-sheet-quality-allowlist.json --json

git diff --check
```

Then start the documented browser-first wizard and create a **fresh** ignored run (the historical run has downstream evidence and must not be reused):

```sh
.venv/bin/python scripts/ingest_wizard_server.py --port 8040
```

Bind the characterization to source `/Users/seandm/Projects/27vette/2027 Chevrolet Car Corvette Export (4) (1).xlsx`, expected SHA-256 `6ac9538d5bb8a823ade9afea70b2654057b793e1cf27c081c088545aa3add8a1`; reuse the exact sheet roles recorded by run `20260717-091317-470292`; select targets `grand_sport_x`, `zr1`, `zr1x` with comparators `grand_sport`, `z06`, `z06`. Compile against the repaired canonical workbook read-only and record deterministic-row counts, individual-review counts by genuine conflict class, and projected full-sheet quality. Do not emit or apply a ChangeSet.

The real-source reprocess passes only when curated copy is preserved, deterministic rows avoid individual review, and every residual subject is a contract-defined conflict. The disposable greenfield fixture passes only when it emits no bad ready row. Both must preserve the source binding and perform no canonical workbook write.

Stop and reopen this spec rather than implementing around the problem if the compiler cannot evaluate the complete desired sheet before readiness or target-owned deletion references cannot be separated between ZR1 and ZR1X. Do not add a model-specific Python exception, weaken the quality gate, force deterministic rows through individual review, bulk-accept a material disagreement, activate a model, or write/publish runtime data to make the tests pass.

**Implementation receipt (2026-07-21):** compiler policy `options-recurrence-prevention-4.4-v1` implements the five-rule contract across `canonical_rows.py`, `parser.py`, `copy_split.py`, `identity.py`, `compiler.py`, `options_sheet_quality.py`, `exceptions.py`, `session.py`, and the ingest-wizard browser. The implementation preserves exact source `detail_raw`, keeps unchanged curated copy, applies the shared `0.60` comparator materiality test, fails closed on all split/queue/quality flags, allocates deterministic target-local ids and section orders, preserves workbook-authoritative behavior, deletes uniquely owned target-specific all-unavailable rows and references, binds the exact quality allowlist path/SHA to authority, and evaluates the complete projected Options sheet before readiness. Copy review cards expose current/proposed copy, complete target raw text, explicit comparator availability/comparison, target statuses, behavior/default, placement/order, and price evidence; browser verification on ZR1 J6O confirmed blank values are explicit and the reviewed-copy fields are populated without truncation.

Validation passed: the focused §4.4 command reports **200 passed, 30 subtests passed**; the final focused compiler/exception/browser rerun reports **92 passed, 7 subtests passed**; the full ingest gate reports **320 passed, 38 subtests passed**; the canonical Options-sheet quality CLI reports `passed` with zero issues; Python compilation, `node --check`, and `git diff --check` pass. Fresh ignored run `20260721-015032-c8e3df` is bound to source SHA-256 `6ac9538d5bb8a823ade9afea70b2654057b793e1cf27c081c088545aa3add8a1`, uses the recorded 20260717 roles and requested GSX/ZR1/ZR1X comparator selection, and produces identical semantic fingerprints on repeated compile. It projects 653 option rows (GSX 239, ZR1 207, ZR1X 207), with 593 ready and 60 blocked; all 278 residual subjects are named contract conflicts, including 23 individual copy reviews and 22 projected-quality blockers (`standard_option_nonzero_price` 20, aggregate stub-name band 2). No ChangeSet was emitted. Receipt: `form-output/ingest-wizard/20260721-015032-c8e3df/4.4-real-source-characterization.json`.

Protected surfaces remained byte-identical through the pass: `stingray_master.xlsx` SHA-256 `31764a718a29f1705961674d97de821e1474f97a4234209fef3a4fe2bce8ece3`; `form-app/data.js` SHA-256 `2848de3842575972a1191c1030d69d16b5be3da7cbd3c10ff37ad0c088f11dd7`. No workbook write, generation, publication, promotion, deployment, or dealer-submission change occurred. Residual risk is limited to the deliberately open, individually reviewable real-source conflicts; resolving them is future review work and is not implied by this implementation pass.

## 5. Explicitly not done

- No replay of the old ChangeSet; no restart of the ingest review; no manual cleanup of all three sheets.
- No `model_master` activation, promotion, registry, runtime contract, or `form-app` change.
- No non-options sheet content cleanup beyond the id cascade.
- No broad copy-standards project beyond the reference-proven predicates.

## 6. Open item for Sean (from both audits)

Commit `281eb14` wrote `stingray_master.xlsx` with no run receipt, against Milestone 3's no-live-write status line. Needs Sean's confirmation on whether that write was separately authorized — independent of this repair.

## 7. Done means

- Lint gate green on gsx/zr1/zr1x with an allowlist Sean has seen: zero name==description, zero description==detail duplication outside allowlist, zero multi-line/oversized names outside allowlist, zero bare-`LPO` names, zero hash-derived option ids, zero null `display_order` on active rows; stub-name count (≤12 chars) at or below the reference-model band (≤6 per sheet, allowlisted).
- ZR1/ZR1X names repaired via Checkpoint-1-approved comparator/identifying-copy proposals; GSX shared rows match the July 9 reviewed decisions or carry recorded overrides; the 8 fresh GSX RPOs are deleted across targets and the 26 no-RPO mappings reuse exact z06 copy deterministically.
- Sean's manual edits (price fills, reordering) intact in the final workbook.
- Every `choose_section` decision reconciled: matches the workbook or has a recorded override.
- Compiler regression tests prove the §1 numbers cannot recur.
- No promotion/registry/runtime/dealer surface changed.
