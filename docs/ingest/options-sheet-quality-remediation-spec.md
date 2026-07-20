# Options Sheet Quality Remediation — GSX / ZR1 / ZR1X

Status: DRAFT awaiting Sean's approval. No workbook writes authorized by this spec until the approval checkpoints below.
Scope: `grand_sport_x_options`, `zr1_options`, `zr1x_options` (and only the referential cascade those fixes force). Promotion, registry, runtime, and dealer surfaces are out of scope.

## 1. Problem — measured, not vibes

Audit substrate: the **working-copy** `stingray_master.xlsx` — Sean was mid-edit, and his edits are real content: at committed `a26c797` gsx has 13 selectable rows with price None; in the working copy 5 of those carry Sean's manual price fills (AQ9/CF7/CM9/R9W → 0, DTC → 1295), leaving 8. The table below reports the working copy; the repair (§4B/C) must diff against the working copy at execution time, treating Sean's manual edits as reviewer decisions to preserve, not drift to revert. (`stingray_options`/`grandSport_options` additionally differ by stale sheet dimensions from an external editor save — phantom empty rows, filtered below.) All probes: openpyxl `read_only=True, data_only=True`, **rows with every cell None excluded** (stale dimensions otherwise inject phantom rows and corrupt counts — see the verifier's lesson in the run receipt).

Executable predicates (these become the §4A lint rules verbatim): duplication = exact string equality; oversize = `len(option_name) > 60`; multi-line = `"\n" in option_name`; stub name = `len(option_name.strip()) <= 12` (catches `LPO`, `Wheels`, `Seats`, `Calipers`, … — reference models have only legitimate short names like paint colors, ≤6 rows each); unpriced-selectable = `selectable is True and price is None`; hex id = no-RPO row with `option_id` matching `opt_std_[0-9a-f]{12,}`.

| Metric | z06 (reference) | grandSport | gsx | zr1 | zr1x |
|---|---|---|---|---|---|
| non-empty rows | 244 | 241 | 247 | 216 | 217 |
| `option_name == description` | 0 | 0 | **51** | 1 | 1 |
| `description == detail_raw` | 0 | 0 | **237** | 3 | 3 |
| newline inside `option_name` | 0 | 0 | **32** | 2 | 2 |
| `option_name` > 60 chars | 0 | 1 | **39** | **98** | **98** |
| max name length | 55 | 65 | **559** | **384** | **384** |
| `display_order` null | 0 | 0 | **237** | 3 | 3 |
| names that are literally `LPO` | 0 | 0 | **49** | 0 | 0 |
| stub names (≤12 chars) | 4 | 4 | **113** | 3 | 3 |
| `active=False` rows | 5 | 3 | **1** | 1 | 1 |
| priced AND not selectable | 2 | 3 | 0 | **11** | **12** |
| selectable AND price None | 6 | 7 | 8 | 2 | 2 |
| no-RPO rows with 16-hex `opt_std_…` ids | 0 | 0 | **26** | 1 | 1 |

ZR1/ZR1X regressed from their own prior scaffolds: the compiler's `update` actions overwrote previously curated names with raw-derived text (98 names >60 chars vs 0 on z06). Example, ZR1 `TDM`: name is a 200-char Teen Driver paragraph. GSX `R6P`-class rows carry full numbered disclosure text inside `option_name`.

## 2. Root causes (all located, all mechanical)

1. **Compiler bypasses the copy rules.** `scripts/corvette_form_generator/ingest/wizard/compiler.py:1552` emits:
   - `option_name` = naive `description.split(",", 1)[0]` — no LPO second-segment rule, no `NEW!+` strip, no newline/disclosure handling, no length bound;
   - `description` = full raw text verbatim;
   - `detail_raw` = the same full raw text.
   The correct, tested rules already exist in `copy_split.py` (`propose_copy_split`: name before first comma; LPO rows take the segment after the `LPO,` prefix; `NEW!+` stripped; disclosure lines split out). They are consumed by the legacy decisions/plan path only — the canonical compiler never calls them.
2. **No-RPO id allocation invents a new convention.** `identity.py:181` allocates `opt_std_<sha16>` for no-RPO rows. Canonical convention (z06) is short sequential `opt_NNN`. GSX greenfield → all 26 SE rows hex; ZR1/ZR1X each picked up one new hex row.
3. **`display_order` has no source.** `compiler.py:1547`: `existing.get("display_order") if existing else ""` — greenfield rows get blank; nothing consults the comparator's per-section ordering or any decision lane.
4. **`active` is derived, not decided.** Only explicit `keep_inactive` retentions (3 recorded) survive; comparator-inactive precedent (z06 has 5, grandSport 3) and Sean's per-option instructions have no lane, so GSX landed with 1.
5. **Price semantics unchecked.** Compiler carries source price onto rows regardless of selectable/standard semantics — standard engine-appearance rows priced (11–12 on ZR1/ZR1X), while some selectable rows have no price. (Note: some priced non-selectable rows are legitimate — R8E gas-guzzler is a mandatory charge; z06 itself has 2. This is a review lane, not a blanket rule.)
6. **Section placements unverified against decisions.** Run `20260717-091317-470292` holds 45 resolved `choose_section` entries (reviewer SeanM/SeanM2) with exact `sectionId` payloads. No reconciliation report was ever produced showing decided-vs-landed placement; Sean reports landed placements are wrong.

## 3. Canonical `*_options` column contract

This is the durable definition the lint gate (§4A) encodes. Reference model: `z06_options`.

- **option_name** — customer-facing label. Single line. Title Case. ≤ 60 chars. Never: `LPO` prefix or bare `LPO`; `NEW!` markers; numbered disclosure lines; "Genuine Corvette Accessory"; raw feature enumerations ("includes …"); text identical to `description` or `detail_raw`. Derivation: `copy_split` rules (segment before first comma; LPO rows use the segment after `LPO,`).
- **description** — optional short customer-facing sentence. Never identical to `option_name` or `detail_raw`. No disclosure numbering.
- **detail_raw** — the one and only column that carries full raw export text (disclosures, includes-lists, footnote lines), preserved verbatim.
- **option_id** — `opt_<rpo>_NNN` for RPO rows; short sequential `opt_NNN` for no-RPO standard rows (z06 convention). No hash-derived ids.
- **section_id** — must equal the resolved `choose_section` decision where one exists; must exist in `section_master`.
- **display_order** — non-null for every active row; monotone within a section; increments of 5 or 10 (z06 pattern).
- **active / selectable** — reviewer-owned flags; comparator precedent proposed, Sean decides; never silently derived from status math alone.
- **price** — populated on selectable orderable rows with a source price; blank on standard rows except reviewer-confirmed mandatory charges (e.g. R8E).

## 4. Deliverables, in order

### A. Lint gate (read-only, permanent) — build first
`tests/test_options_sheet_quality.py` (or extension of `test_editor_lints.py`): machine checks for every §3 rule, parameterized over all `*_options` sheets, with a per-model allowlist file for reviewed exceptions (mandatory-charge prices, the two >60-char legacy names on stingray/grandSport, etc.). Runs in the normal pytest gate and is required green by any future promotion gate. **This is the anti-drift mechanism — it lands before any repair so the repair is graded by it.**

### B. Reconciliation report (read-only)
One script emitting one Markdown/JSON report per model:
1. `choose_section` decisions from run `20260717-091317-470292` joined to landed `section_id` — every mismatch listed by RPO.
2. Copy repair preview: current name/description/detail vs `copy_split`-derived proposal, per row.
3. Id repair preview: hex `opt_std_*` → proposed sequential ids, plus the full cross-sheet reference cascade (`*_ovs`, `*_price_rules`, `*_rule_*`, `*_exclusive_*`, `default_selection_rules`) that each rename touches.
4. `display_order` proposal: comparator section ordering (z06 for ZR1/ZR1X; grandSport/z06 hybrid per prior GSX decisions) with gaps flagged for Sean.
5. `active`/price review lanes: proposed flags with comparator precedent cited; priced-standard rows and unpriced-selectable rows listed for accept/override.
6. ZR1/ZR1X curated-name restore: diff current sheets against pre-integration workbook (`git show 281eb14^:stingray_master.xlsx`); where an option existed before with a clean name and the compiler clobbered it, propose restoring the prior name. Greenfield GSX has no prior state — its names come from rule derivation only.

**Checkpoint 1: Sean reviews the report and marks accepts/overrides.** This is where his placement/active/price instructions get recorded once, durably.

### C. Repair changeset (single bounded apply)
Deterministic script consuming the approved report → one `editor_ops.apply_batch()` changeset touching only the three `*_options` sheets plus the exact referential cascade from B.3. Dry-run report first (op counts, before/after per row, workbook fingerprint check).

**Checkpoint 2: Sean approves dry-run → live write via the existing safe-save path.** Post-apply: readback verification + lint gate (A) green on all three sheets.

### D. Compiler fixes (stop it happening again)
Same rules pushed into the pipeline so the next ingest run can't reproduce the mess:
1. `compiler.py:1552` routes name/description/detail through `copy_split.propose_copy_split`.
2. `identity.py:181` allocates sequential no-RPO ids against the reserved set.
3. `display_order`: greenfield rows draw from comparator section ordering; blank only with an explicit typed exception.
4. `update` actions never overwrite curated `option_name`/`description` with raw-derived text when the existing value already passes the §3 lint — raw text lands in `detail_raw` only.
5. Regression tests: fixture rows forcing the LPO branch, the NEW! marker, a multi-line disclosure name, a no-RPO id allocation, and a curated-name-preservation update (per the fixture-shadowed-branch failure mode in the loop skill).

D can proceed in parallel with B/C review but must land with its tests before any future compiler run against real data.

## 5. Explicitly out of scope
- Any `model_master` activation, promotion, registry, runtime contract, or `form-app` change.
- Non-options sheet cleanups (ovs/rules/pricing content beyond the id cascade).
- Sheet-family naming drift (`grand_sport_x_rule_members` vs `*_rule_group_members` pattern) — cosmetic, registered consistently in `model_workbook_sources`; separate pass if desired.

## 6. Done means
- Lint gate green on gsx/zr1/zr1x with an allowlist Sean has seen.
- Zero name==description rows, zero description==detail duplication outside allowlist, zero multi-line/oversized names, zero bare-`LPO` names, stub-name count (≤12 chars) at or below the reference-model band (≤6 per sheet, allowlisted), zero hex option ids, zero null display_order on active rows.
- Every `choose_section` decision from the run matches the workbook or carries a recorded Sean override.
- Compiler regression tests prove the same input can no longer emit the §1 numbers.
