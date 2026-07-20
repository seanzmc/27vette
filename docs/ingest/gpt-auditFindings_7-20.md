You are not back at square one. The underlying reviewed work still exists, and the three sheets can be recovered without repeating the ingest process or manually fixing hundreds of rows.

The immediate problem is the canonical compiler. It discarded the existing copy-splitting and display-order behavior, then emitted malformed rows into an otherwise valid ChangeSet. The workbook service faithfully wrote those rows—it did not corrupt good rows during application.

### What I confirmed

| Sheet | Rows | Blank display order | Description = raw detail | Names >80 chars | Long hashed no-RPO IDs |
|---|---:|---:|---:|---:|---:|
| `grand_sport_x_options` | 247 | 237 | 237 | 37 | 26 |
| `zr1_options` | 216 | 3 | 3 | 58 | 1 |
| `zr1x_options` | 217 | 3 | 3 | 59 | 1 |
| Promoted comparison sheets | 241–244 | 0 | 0 | 0 | 0 |

GSX also has 77 names that are effectively generic stubs and only one inactive row. This directly confirms what you saw. :codex-file-citation{path="/Users/seandm/Projects/27vette/stingray_master.xlsx" artifact_kind="workbook" sheet="grand_sport_x_options" range="A1:K248"} :codex-file-citation{path="/Users/seandm/Projects/27vette/stingray_master.xlsx" artifact_kind="workbook" sheet="zr1_options" range="A1:K217"} :codex-file-citation{path="/Users/seandm/Projects/27vette/stingray_master.xlsx" artifact_kind="workbook" sheet="zr1x_options" range="A1:K218"}

The failure is visible in [compiler.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/ingest/wizard/compiler.py:1547):

- New rows get blank `display_order`.
- `option_name` is merely everything before the first comma.
- `description` and `detail_raw` both receive the complete raw source text.
- Standard pricing becomes zero only under a narrow all-variants-standard condition.

That bypasses the rules already implemented in [copy_split.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/ingest/wizard/copy_split.py:79) and previously consumed correctly by [plan_builder.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/ingest/wizard/plan_builder.py:811). Those rules include the LPO handling, `NEW!` removal, disclosure splitting, raw-detail preservation, review flags, and deterministic section-local display order.

The regression escaped because [workbook-visual-copy-standardization.test.mjs](/Users/seandm/Projects/27vette/tests/workbook-visual-copy-standardization.test.mjs:5) only checks Stingray, Grand Sport, and Z06—not these unpromoted sheets. The deployment proof tested structural/runtime consistency, not whether the copy itself was presentable.

### The quickest accurate recovery

1. **Freeze the current workbook as the recovery baseline.**  
   Preserve your GSX row reordering and the five detected price edits: AQ9, CF7, CM9, DTC, and R9W. Do not revert the workbook wholesale.

2. **Generate one read-only corrected projection—not another ingest run.**

   - For ZR1 and ZR1X, use the pre-integration workbook as the baseline because almost all those rows already existed. The integration added only three option rows per sheet while overwriting existing copy.
   - For GSX, recover the 203 shared RPO rows from the already-reviewed [July 9 plan](/Users/seandm/Projects/27vette/form-output/ingest-wizard/20260709-184223-960eb1/apply-plan.json), but retain the current raw-detail evidence and your current price edits.
   - Keep the ten current GSX paint rows, which are already substantially correct.
   - Map the 26 no-RPO standard rows to the corresponding promoted-model rows, giving them short sequential workbook IDs and curated copy.
   - Review only the eight GSX RPOs absent from the reviewed plan: N26, PRB, R6P, R9L, R9V, R9W, R9Y, and TU7. Several are currently selectable inside the standard-equipment section, so they require explicit placement/status confirmation.

3. **Show you only the residual diff.**  
   The report should contain before/after copy, section, price, active/selectable, order, and ID changes. It should not send hundreds of already-reviewed rows back through the wizard. Existing decisions must be reused only when their candidate fingerprints still match.

4. **After your review, produce one bounded ChangeSet.**  
   It should touch only the three option sheets plus exact foreign-key references required by changed option IDs. First apply it to a temporary workbook and run copy-quality, package, schema, reference, generation, and runtime-contract checks. A live workbook write remains a later explicit approval.

5. **Fix the compiler before it is allowed to process another real model.**  
   Route canonical rows through `propose_copy_split()`, allocate display order, preserve curated existing copy, and add content tests covering unpromoted sheets. This should follow the recovery projection; it should not delay getting the workbook reviewable.

### What I would not do

I would not replay the old ChangeSet, restart the entire ingest review, or manually clean all three sheets.

A new concurrent draft, [options-sheet-quality-remediation-spec.md](/Users/seandm/Projects/27vette/docs/ingest/options-sheet-quality-remediation-spec.md), appeared while I was auditing. I did not create it. It identifies much of the same root cause, but I would not execute it as written: it makes a broad permanent lint project a prerequisite, invents some rigid copy rules, and proposes comparator display-order copying even though the canonical design explicitly says comparator order is not copied. That is precisely the sort of expansion that will prolong this.

No workbook, generated artifact, source file, promotion state, registry, runtime, deployment, or dealer behavior was changed by this audit. I removed my temporary audit worktrees and files. The workbook plus the concurrently created draft/run files remain untouched.