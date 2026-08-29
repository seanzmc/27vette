# Workbook Manager Audit Report

Workbook Manager is a functional, safety-conscious editor for much of the operational workbook, but it is not yet a complete or dependable replacement for direct workbook maintenance.

The guarded draft → validate → approve → apply/rebuild pipeline works, including durable draft recovery, rollback, regeneration, publication, and verified re-import. The largest deficiencies are management coverage, audit/recovery UX, and a few misleading scope/error displays that could cause an operator to approve or troubleshoot the wrong thing.

No repository files were changed and no PR was created.

## 1. Executive summary

### Audit basis

- Frontend: React/Vite source under workbook-manager/frontend/src/; built UI served from workbook-manager/frontend/dist/.
- Backend: FastAPI under workbook-manager/backend/app/.
- Runtime command: ./workbook-manager/run.sh, single-process Uvicorn.
- Default canonical workbook: /Users/seandm/Projects/27vette/stingray_master.xlsx.
- Default disposable projection: workbook-manager/var/workbook_projection.sqlite3.
- Default durable state: workbook-manager/var/workbook_manager.sqlite3.
- Specialized outputs:
  - comparison exports under workbook-manager/var/exports/
  - state backups under workbook-manager/var/db-backups/
  - apply rollback sets under workbook-manager/var/apply-rebuild-rollbacks/
- Major workspaces:
  - Form Overview
  - Sections & Layout
  - Options & Relationships
  - Groups
  - Images
  - Review & Apply
  - Advanced & Recovery

### Execution approach

I ran the current built UI against an isolated copy of the current workbook and isolated SQLite/output paths. The source workbook copy began with SHA-256:

3127e663b1531e366ce86b989b6190914108d40dfd15a33a258307a05d608e3c

The first-run UI imported that workbook successfully with zero blocking findings. I then exercised every top-level workspace, every distinct control/action type, all six models, and all 16 raw collections for every model—96 model/collection combinations.

I also completed a real isolated write round trip:

1. Opened Stingray Z51.
2. Changed its name through the connected editor.
3. Saved to the durable draft.
4. Reloaded the browser and confirmed draft persistence.
5. Locked the draft.
6. Ran workbook validation.
7. Approved it.
8. Typed the apply confirmation.
9. Applied and rebuilt.
10. Verified the workbook cell from disk.
11. Verified the generated Stingray contract and form-app/data.js.
12. Re-imported the changed workbook.
13. Confirmed the new value in the connected UI.

The successful apply reported:

- workbook: applied
- projection: stale until re-import
- generated contracts: current, Stingray
- publication: current
- data.js cache version: 37 → 38

After re-import, the UI displayed the applied value.

Coverage summary

The live workbook contains 77 sheets:

- 72 classified by the Manager as writable workbook families
- 1 managed read-only sheet
- 4 preserved but unprojected sheets

Grouped into 30 meaningful workbook/data areas, actual UI coverage is:

- View + Edit: 19
- View Only: 5
- Indirectly Represented: 2
- Not Represented: 4

That count overstates practical completeness because several “View + Edit” groups are available only as raw tables and lack coordinated relationship or bulk workflows.

### Bottom line

_What works:_

- Importing and validating the current workbook
- Browsing six models
- Editing most option/rule/group/pricing/interior/asset data
- Durable draft persistence
- Add/update/delete intent
- Connected option and group editing
- Image reconciliation and asset-map drafting
- Validation, approval, guarded workbook write, regeneration, publication
- Rollback after downstream failure
- Comparison export and durable-state backup

_What prevents it from being a complete workbook-management tool:_

- Important registered structure tables are visible only indirectly or entirely uneditable.
- Four meaningful workbook sheets are not represented at all.
- Current applied changes never appear in the visible Change History.
- A rejected immutable draft cannot be fixed despite the UI telling the user to fix and revalidate it.
- Apply errors can be stored but hidden behind “No recorded warnings or failures.”
- Review can show the union of all affected models on every individual change.
- Image “Clear filters” can leave the global model header saying one model while showing all-model results.
- Graph operations such as adding an option or deleting a highly connected option require many manual raw-table operations.

## 2. Actual functionality map

Surface: First-run/import
Actual status: Working
Observed behavior: Missing projection presents reload/import controls; import produced a verified current projection.
────────────────────────────────────────
Surface: Status banner/system details
Actual status: Working, terse
Observed behavior: Separates projection, draft, workbook, generated artifact, and publication state. Details are compact and sometimes too terse during failures.
────────────────────────────────────────
Surface: Model switching
Actual status: Working
Observed behavior: Cards and global model selector switched among all six models.
────────────────────────────────────────
Surface: Form Overview
Actual status: Working, partial management
Observed behavior: Displays model cards, steps, sections, buckets, summary mappings, inactive counts, and variants. Only model metadata, existing steps, context sections, and section-presentation rows are editable.
────────────────────────────────────────
Surface: Sections & Layout
Actual status: Working
Observed behavior: All filters returned coherent sets; connected section details and option navigation worked.
────────────────────────────────────────
Surface: Options & Relationships
Actual status: Working, noisy
Observed behavior: Search, connected detail, diagnostics, option editing, rule/group links, availability, and draft overlays worked. Search often returns many indirect text matches.
────────────────────────────────────────
Surface: Groups
Actual status: Working, search-only
Observed behavior: Group search/detail, group facts, membership add/remove/reorder/active controls worked. No browse index is provided.
────────────────────────────────────────
Surface: Images
Actual status: Working, partial
Observed behavior: Live reconciliation loaded 290 media URLs. Coverage, status queues, filtering, pagination, safe proposals, presentation edits, manual inventory lookup, assignment, ignore, and durable evidence are present. Several triage workflows are unnecessarily difficult or misleading.
────────────────────────────────────────
Surface: Review & Apply
Actual status: Core pipeline working
Observed behavior: Draft persistence, commit, preview, approval, typed apply, rollback, retry, successful apply, generation/publication, and re-import all worked. Correction and error-presentation gaps remain.
────────────────────────────────────────
Surface: Advanced raw collections
Actual status: Working
Observed behavior: All 96 model/collection combinations loaded. Search, pagination, add, edit, dependency inspection, and delete intent worked.
────────────────────────────────────────
Surface: Current Change History
Actual status: Broken
Observed behavior: A successfully applied current draft still produced “0 records / No committed changes yet.”
────────────────────────────────────────
Surface: Comparison export
Actual status: Working
Observed behavior: Produced a DISPOSABLE-comparison-\*.xlsx file.
────────────────────────────────────────
Surface: Draft/history backup
Actual status: Working
Observed behavior: Produced a durable-state SQLite backup and displayed its path.
────────────────────────────────────────
Surface: Narrow/mobile layout
Actual status: Mostly working
Observed behavior: Six primary workspaces fit at 390 px; Advanced overflowed the document to 1183 px.
────────────────────────────────────────
Surface: Legacy staging/sync APIs
Actual status: Unreachable from current UI
Observed behavior: Backend routes remain, but the browser uses the durable draft lifecycle.

## 3. Prioritized findings

### WM-001 — High — Advanced & Recovery / Change History

#### **Problem**

The visible “Change History (append-only audit)” does not show changes applied through the current durable draft workflow.

#### **User impact**

An operator can successfully write and rebuild a workbook, then open the application’s audit-history panel and be told no committed changes exist. This makes the visible audit surface materially unreliable.

Reproduction

1. Edit and save an option.
2. Lock, validate, approve, and apply/rebuild.
3. Re-import the changed workbook.
4. Open Advanced & Recovery.
5. Inspect Change History.

Actual behavior
The applied draft existed with status applied and one operation, but the UI showed:

- 0 record(s)
- No committed changes yet.

Supporting evidence

- workbook-manager/frontend/src/components/HistoryView.jsx:12-18 loads /api/history.
- HistoryView.jsx:22 labels it append-only audit history.
- HistoryView.jsx:44-45 displays “No committed changes yet.”
- workbook-manager/backend/app/main.py:1753-1780 reads only the legacy change_history table.
- Current applied-draft evidence is stored in workflow_drafts and draft_apply_attempts; the legacy staging path is what appends change_history in workbook-manager/backend/app/staging.py:415-424.

#### **Recommended direction**

Replace or supplement this panel with durable workflow history: terminal drafts, operations, preview/approval/apply attempts, actor, workbook hashes, affected models, and write/rebuild outcome. If the legacy table remains, label it explicitly as legacy staging history rather than the Manager’s audit history.

### WM-002 — High — Form Overview / workbook structure management

#### Problem

Several workbook families are registered as writable in the backend but have no user-accessible editing workflow.

Affected data

- model_registry_promotion
- model_workbook_sources
- variant_master
- model_variants
- order_summary_sections
- step_order_summary_map

#### User impact

Promotion, source routing, variant definitions/membership, and summary organization still require direct workbook editing. These are foundational workbook-management functions, not fringe metadata.

Reproduction

1. Inspect Form Overview.
2. Open the model editor and every step/section editor.
3. Open Advanced & Recovery and sweep every collection tab.
4. Search for editors for promotion, workbook sources, variants, and summary mappings.

Actual behavior

- Promotion is reduced to Runtime/Default badges.
- Variants are shown in a collapsed read-only table.
- Summary mappings are shown as cards.
- Workbook source routing appears only indirectly through collection availability and lineage.
- None has create/edit/delete controls.

Supporting evidence

- Backend structure-table inventory includes these tables at workbook-manager/backend/app/catalog.py:347-359.
- /api/tables exposes their writable schemas at workbook-manager/backend/app/main.py:810-813.
- Advanced collection routing uses MODEL_COLLECTIONS, which excludes them: catalog.py:332-346 and main.py:511-560.
- Form Overview only opens editors for models, form_steps, context_sections, and section_presentation: workbook-manager/frontend/src/components/FormStructure.jsx:106-167,208-222.
- Variants are rendered without controls at FormStructure.jsx:340-363.

#### Recommended direction

Expose every registered writable structure table through the same schema-driven editor shell. Prefer contextual workflows for promotion, variant membership, and summary mapping, while retaining a raw structure-table fallback.

### WM-003 — High — Review & Apply / draft correction

#### Problem

A validation-rejected draft cannot be corrected, despite the UI instructing the user to fix it and revalidate.

#### User impact

One bad operation can force the user to discard and recreate an entire multi-operation draft. The problem also exists before locking: Review has no per-operation remove/discard control.

Reproduction

1. Add an option through Advanced.
2. Do not add its six required OVS records.
3. Lock the draft.
4. Run validation.

Actual behavior

- Validation correctly reported six missing OVS rows.
- State card said: “Next: Fix the reported problems, then revalidate.”
- The only lifecycle action was “Cancel Draft and Keep Audit Record.”
- No editor, unlock, clone, per-operation removal, or revalidate action was available.

Supporting evidence

- The misleading instruction is hardcoded at workbook-manager/frontend/src/components/ChangesSync.jsx:37-49.
- canPreview excludes preview_rejected at ChangesSync.jsx:236-243.
- Draft-operation rendering has no removal controls at ChangesSync.jsx:352-405.
- The browser API exposes POST/GET operations but no operation-discard route.

#### Recommended direction

Provide at least one safe correction path:

- clone/fork a rejected immutable draft into a new mutable draft;
- remove selected operations from a mutable draft;
- or return to source editors with an explicit replacement draft.

The original immutable ChangeSet and rejected attempt should remain in the audit record.

### WM-004 — High — Review & Apply / apply failure evidence

#### Problem

An apply failure can be recorded in the durable attempt while the UI says “No recorded warnings or failures.”

#### User impact

The operator sees “Write did not finish (restored)” but is not shown the reason needed to fix the environment or safely decide whether to retry.

Reproduction

1. Run Apply and Rebuild with an incomplete isolated output baseline.
2. Generation/publication fails because another promoted model artifact is unavailable.
3. Inspect the failure card and Warnings & failures panel.

Actual behavior

- Rollback succeeded and the workbook hash was restored.
- The durable apply attempt contained the exact FileNotFoundError.
- The visible Warnings & failures panel said “No recorded warnings or failures.”
- The reason was available only inside the expandable raw attempt JSON.

Supporting evidence

- Apply failures populate result.errors at workbook-manager/backend/app/apply_rebuild.py:418-451.
- The UI’s empty-state condition checks preview and approval messages but omits apply messages: workbook-manager/frontend/src/components/ChangesSync.jsx:604-615.
- The render branch would include messages(applyAttempt), but that branch is skipped when only the apply attempt has errors.

#### Recommended direction

Include apply-attempt errors in the empty-state condition and show a concise failure summary above the raw JSON, including failed stage, exception, rollback state, and safe next action.

### WM-005 — High — Review & Apply / affected-model scope

#### Problem

Every review entity is labeled with the draft-wide union of affected models rather than that entity’s own model context.

#### User impact

In a mixed-model draft, a reviewer cannot trust the scope shown beside an individual change. This can exaggerate or obscure the actual models affected by that row.

Reproduction

1. Create a mixed draft containing a Stingray option update and a Grand Sport asset update.
2. Open Review & Apply.

Actual behavior
Both individual entries displayed affects grand_sport, stingray, even though their underlying operations had different ownership.

Supporting evidence
workbook-manager/frontend/src/components/ChangesSync.jsx:306-308 renders review.affected_models—the whole-draft union—for every entity.

#### Recommended direction

Render entity- or operation-specific model_context beside each entry. Keep the draft-wide union only in a separate draft summary.

### WM-006 — High — Images / model scoping

#### Problem

Problem
“Clear filters” can switch the Images inbox to all models without updating the global model context.

#### User impact

The header can say ZR1X while the first actionable card belongs to Grand Sport. A user can therefore stage an image decision for the wrong model while believing the global model selector scopes the workspace.

Reproduction

1. Select ZR1X globally.
2. Open Images.
3. Click Clear filters.
4. Open the first safe or covered item.

Actual behavior

- Global header remained ZR1X.
- Image model filter became All models.
- Grand Sport records appeared and were editable.

Supporting evidence

- Images initializes its local model filter from global context at workbook-manager/frontend/src/components/AssetManager.jsx:145-148.
- Model filter changes update global context only when the value is nonblank: AssetManager.jsx:199-207.
- Clear filters directly sets the local model to "" without updating global context: AssetManager.jsx:347-350.

#### Recommended direction

Either preserve the selected global model when clearing secondary filters, or explicitly change the application context to an “All models” state that is equally visible in the header and Review.

### WM-007 — Medium — Advanced raw browser / delete and workflow continuity

#### Problem

A row with no dependents is staged for deletion immediately on one icon click, with no confirmation. Saving also resets Advanced back to the default Options collection and clears the user’s working context.

#### User impact

A user can accidentally add a delete operation, then lose the table/search/page they were using. Repeated maintenance becomes slow and error-prone.

Reproduction

1. Open Rule Mappings.
2. Search for a rule with no dependents.
3. Click the trash icon once.

Actual behavior

- The delete operation was saved immediately.
- No confirmation appeared.
- Global refresh unmounted Advanced.
- The workspace returned to the first Options collection with the search cleared.

Supporting evidence

- No-dependent deletion calls saveDelete() immediately: workbook-manager/frontend/src/components/ModelOperations.jsx:94-106.
- The icon title is “Save delete to draft”: ModelOperations.jsx:230-236.
- Save triggers global onChanged() at ModelOperations.jsx:76-89.
- Global status refresh temporarily makes the application not ready and unmounts workspaces: workbook-manager/frontend/src/App.jsx:55-60,171,354-369.

#### Recommended direction

Require a lightweight confirmation or provide an immediate Undo. Refresh only draft evidence in place, preserving selected model, collection, search, offset, scroll, and editor context.

### WM-008 — Medium — Option creation and dependent deletion

#### Problem

Graph operations are exposed as isolated raw-row actions rather than coordinated workflows.

#### User impact

- Adding one option requires manually creating all active-variant OVS rows.
- Deleting a connected option can require deleting dozens of dependents one by one.
- Validation detects incompleteness only after the draft is locked.

Reproduction

- Option add: add one option, lock, validate; the audit option was rejected for six missing Stingray OVS rows.
- Option delete: inspect deletion of Z51; the UI listed 25 dependent records and offered only “Save parent delete to draft.”

Actual behavior
The UI explains final-graph validation but offers no OVS matrix, dependent-selection plan, cascade preview, or bulk drafting.

#### Recommended direction

Add coordinated workflows:

- “Add option” with required variant availability matrix.
- “Delete option/group” dependency plan where the operator explicitly selects/removes the complete graph.
- Bulk relationship operations that still emit ordinary typed draft rows.

### WM-009 — Medium — Images / unresolved media triage

#### Problem

Several image-resolution controls are technically present but impractical or incomplete.

Verified examples

- A missing-image search with no matches produced no “no results” feedback.
- The unmatched-media target selector contained 837 options in one unsearchable select.
- The top overall coverage tile is rendered as a button but has no click handler.
- A wildcard conflict offers only “Save presentation edits to draft”; the specialized workspace does not explain how that resolves—or does not resolve—the conflict.

Supporting evidence

- Media search has no error state/catch: workbook-manager/frontend/src/components/AssetManager.jsx:468-475.
- Inventory controls render only when results exist, with no empty message: AssetManager.jsx:644-660.
- Assignment is one raw select over all targets: AssetManager.jsx:681-691.
- CoverageCard always returns a button at AssetManager.jsx:89-96, while the overall card is created without onClick at AssetManager.jsx:274-285.
- Wildcard conflicts share only the presentation-edit action with covered records: AssetManager.jsx:719-722.

#### Recommended direction

Add explicit no-results/error feedback, a searchable/paged target picker, make the overall card noninteractive or functional, and distinguish “edit presentation” from “resolve wildcard ownership conflict.”

### WM-010 — Medium — Connected option detail / draft-effective values

#### Problem

After an option edit is saved, the connected detail keeps rendering base-projection values instead of the draft-effective value.

#### User impact

The page shows “Draft modified” but the title/copy can still show the old value. The user must reopen the editor or inspect Review to see the actual proposed value.

Reproduction

1. Change Z51’s option name.
2. Save to the draft.
3. Close the editor or reload the page.

Actual behavior
The detail heading remained Z51 — Z51 Performance Package; only the draft badge and editor overlay showed the proposed value.

Supporting evidence
workbook-manager/frontend/src/components/ConnectedExplorer.jsx:132-150 renders detail.option directly, while the draft overlay is only a status banner at ConnectedExplorer.jsx:18-33.

#### Recommended direction

Render an explicit draft-effective value alongside the authored/base value, with clear before/after treatment.

### WM-011 — Low — Navigation, search, and layout

#### Problem

Several interaction patterns are unnecessarily noisy for a first-time operator.

Observed behavior

- Groups has no browse list; the screen is nearly empty until a search is entered.
- Searching Z51 returned a mixture of direct option matches, related rules, and many options whose description/detail text mentioned Z51.
- Running diagnostics appended results below the retained search results instead of replacing or clearly separating the current task.
- The query string persisted while changing unrelated workspaces.
- At a 390 px viewport, Advanced produced document-level width of 1183 px; the other six workspaces stayed at 390 px.

Supporting evidence

- Search intentionally scans description/detail text and rules: workbook-manager/backend/app/explorer.py:338-403.
- Navigation always preserves query: workbook-manager/frontend/src/navigationState.js:21-40.
- Advanced raw tables and controls are not fully contained at the narrow breakpoint.

#### Recommended direction

Add a browse/index mode for Groups, label direct versus mention/relationship matches, make diagnostics a distinct result mode, clear irrelevant query state on workspace changes, and contain Advanced overflow inside the table panel.

## 4. Workbook coverage matrix

Legend:

- V+E: View + Edit
- VO: View Only
- IM: Indirectly Managed/represented
- NR: Not Represented

Workbook group/sheets: model_master
Main fields: identity, labels, year, slugs, active/default, Vehicle Setup copy, notes
Coverage: V+E
Actual UI and limitations: Form Overview edits existing rows only; no model create/delete.
────────────────────────────────────────
Workbook group/sheets: model_registry_promotion
Main fields: promotion, artifact path/type, alias, order, active/default
Coverage: VO
Actual UI and limitations: Runtime/default badges only; most fields invisible and all edits inaccessible.
────────────────────────────────────────
Workbook group/sheets: model_workbook_sources
Main fields: model, source role, sheet, active, notes
Coverage: IM
Actual UI and limitations: Drives collection tabs and lineage; no direct view/editor.
────────────────────────────────────────
Workbook group/sheets: variant_master
Main fields: trim/body/name/base price/order/active
Coverage: VO
Actual UI and limitations: Collapsed Variant reference table; no editing.
────────────────────────────────────────
Workbook group/sheets: model_variants
Main fields: model membership/order/active/notes
Coverage: IM
Actual UI and limitations: Affects displayed variants/order; no direct workflow.
────────────────────────────────────────
Workbook group/sheets: section_master
Main fields: identity/name/mode/required/order/behavior/step
Coverage: VO
Actual UI and limitations: Visible in sections and Advanced; explicitly read-only.
────────────────────────────────────────
Workbook group/sheets: context_section_master
Main fields: context, copy, selection behavior, placement, active
Coverage: V+E
Actual UI and limitations: Existing-row editing; no create/delete.
────────────────────────────────────────
Workbook group/sheets: section_presentation
Main fields: label, step/display behavior/order/buckets/active
Coverage: V+E
Actual UI and limitations: Existing edit and new metadata rows; no delete.
────────────────────────────────────────
Workbook group/sheets: runtime_steps
Main fields: key/label/order/source/active/notes
Coverage: V+E
Actual UI and limitations: Existing-row edit only; no create/delete.
────────────────────────────────────────
Workbook group/sheets: context_choice_copy
Main fields: context values, body-style copy/tooltips
Coverage: NR
Actual UI and limitations: No UI or projection. Manual workbook editing required.
────────────────────────────────────────
Workbook group/sheets: order_summary_sections
Main fields: key/label/order/active/notes
Coverage: VO
Actual UI and limitations: Rendered as summary cards; no direct fields or edits.
────────────────────────────────────────
Workbook group/sheets: step_order_summary_map
Main fields: step-to-summary mapping, active, notes
Coverage: VO
Actual UI and limitations: Combined summary display only.
────────────────────────────────────────
Workbook group/sheets: default_selection_rules
Main fields: target, condition, scopes, priority, display behavior
Coverage: V+E
Actual UI and limitations: Raw Advanced CRUD.
────────────────────────────────────────
Workbook group/sheets: runtime_rule_exceptions
Main fields: option relationship exceptions/scopes/reason
Coverage: NR
Actual UI and limitations: Empty current sheet and no Manager workflow.
────────────────────────────────────────
Workbook group/sheets: All \*\_variant_overrides
Main fields: option/variant selectability, placement, behavior
Coverage: V+E
Actual UI and limitations: Raw Advanced CRUD; shown read-only in section details.
────────────────────────────────────────
Workbook group/sheets: asset_map
Main fields: target, URLs/alts, fit/position/hover, active/notes
Coverage: V+E
Actual UI and limitations: Images workflows plus raw Advanced CRUD.
────────────────────────────────────────
Workbook group/sheets: PriceRef
Main fields: option type, trim, code, price
Coverage: NR
Actual UI and limitations: No projection or editor. Manual workbook editing required.
────────────────────────────────────────
Workbook group/sheets: lt_interiors, LZ_Interiors
Main fields: interior identity/copy/price/material/trim/seat/options
Coverage: V+E
Actual UI and limitations: Unified shared Interiors raw collection; full row editor.
────────────────────────────────────────
Workbook group/sheets: model_interior_scope
Main fields: model/interior/trim plus hierarchy/grouping metadata
Coverage: V+E
Actual UI and limitations: Raw Advanced CRUD.
────────────────────────────────────────
Workbook group/sheets: interior_components
Main fields: model/interior/RPO/type/price references/order
Coverage: V+E
Actual UI and limitations: Raw Advanced CRUD.
────────────────────────────────────────
Workbook group/sheets: color_overrides, grand_sport_x_color_overrides
Main fields: interior/option/rule/adds-RPO
Coverage: V+E
Actual UI and limitations: Unified shared raw collection.
────────────────────────────────────────
Workbook group/sheets: All six option sheets
Main fields: identity, RPO, price, copy, section, selectable/order/active
Coverage: V+E
Actual UI and limitations: Connected editor and raw CRUD; create lacks coordinated OVS workflow.
────────────────────────────────────────
Workbook group/sheets: All six OVS sheets
Main fields: option, variant, status
Coverage: V+E
Actual UI and limitations: Connected view and raw CRUD; no matrix/bulk editor.
────────────────────────────────────────
Workbook group/sheets: All six rule-mapping sheets
Main fields: source/type/target, raw copy, scope/action/disable
Coverage: V+E
Actual UI and limitations: Connected view and raw CRUD; no relationship composer.
────────────────────────────────────────
Workbook group/sheets: All six rule-group sheets
Main fields: label/type/source/scopes/active/notes
Coverage: V+E
Actual UI and limitations: Group contextual editor and raw CRUD.
────────────────────────────────────────
Workbook group/sheets: All six rule-member sheets
Main fields: group/target/order/active
Coverage: V+E
Actual UI and limitations: Group member manager and raw CRUD.
────────────────────────────────────────
Workbook group/sheets: All six exclusive-group sheets
Main fields: label/mode/active/notes
Coverage: V+E
Actual UI and limitations: Group contextual editor and raw CRUD.
────────────────────────────────────────
Workbook group/sheets: All six exclusive-member sheets
Main fields: group/option/order/active
Coverage: V+E
Actual UI and limitations: Group member manager and raw CRUD.
────────────────────────────────────────
Workbook group/sheets: All six price-rule sheets
Main fields: condition/type/target/value/scopes/notes
Coverage: V+E
Actual UI and limitations: Counts in connected detail; raw Advanced CRUD.
────────────────────────────────────────
Workbook group/sheets: rule_phrase_map
Main fields: phrase/type/direction/stop phrases/default/active
Coverage: NR
Actual UI and limitations: No UI or projection. Manual workbook editing required.

The four unprojected preserved sheets contain 33 current data rows in total:

- PriceRef: 21
- context_choice_copy: 6
- rule_phrase_map: 6
- runtime_rule_exceptions: 0

The importer explicitly records these as preserved workbook surfaces without projecting their rows: workbook-manager/backend/app/importer.py:153-190.

## 5. Editing capability matrix

Capability: Edit an existing option
Actual status: Working
Notes: Durable draft persisted through browser reload and full apply.
────────────────────────────────────────
Capability: Edit model copy/metadata
Actual status: Working, update-only
Notes: No model create/delete.
────────────────────────────────────────
Capability: Edit existing runtime step
Actual status: Working, update-only
Notes: No step create/delete.
────────────────────────────────────────
Capability: Edit context/section presentation
Actual status: Working, partial CRUD
Notes: Can add section-presentation rows; no delete.
────────────────────────────────────────
Capability: Create raw records
Actual status: Working for Advanced collections
Notes: Validates required fields and references.
────────────────────────────────────────
Capability: Delete raw records
Actual status: Working but risky
Notes: No-dependency delete is immediate; dependent delete is manual graph assembly.
────────────────────────────────────────
Capability: Edit groups
Actual status: Working
Notes: Group facts and member management available after search.
────────────────────────────────────────
Capability: Add/reorder/remove group members
Actual status: Working
Notes: Searchable option picker; durable draft operations.
────────────────────────────────────────
Capability: Edit rule mappings/pricing/defaults
Actual status: Working as raw rows
Notes: No higher-level rule or pricing composer.
────────────────────────────────────────
Capability: Bulk operations
Actual status: Very limited
Notes: Images “Add all safe matches” only. No general bulk edit, OVS matrix, or relationship batch.
────────────────────────────────────────
Capability: Undo one draft operation
Actual status: Missing/unclear
Notes: Updates can sometimes be reverted through the editor, but Review has no discard control; adds/deletes have no obvious inverse workflow.
────────────────────────────────────────
Capability: Fix rejected draft
Actual status: Broken
Notes: Must cancel and recreate.
────────────────────────────────────────
Capability: Draft persistence
Actual status: Working
Notes: Recovered after hard reload.
────────────────────────────────────────
Capability: Apply persistence
Actual status: Working
Notes: Workbook, generated contract, registry, cache version, re-import, and UI readback verified.
────────────────────────────────────────
Capability: Rollback
Actual status: Working
Notes: Failed downstream attempt restored and hash-verified the workbook and outputs.
────────────────────────────────────────
Capability: Current applied-history view
Actual status: Broken
Notes: Visible History remains empty.
────────────────────────────────────────
Capability: Comparison export
Actual status: Working
Notes: Explicit disposable workbook generated.
────────────────────────────────────────
Capability: Durable-state backup
Actual status: Working
Notes: SQLite backup generated and path displayed.

No sampled field was found to silently disappear from the durable draft or successful workbook write. The persistence problems found are primarily presentation/history problems, not loss of the saved operation.

## 6. Dead ends and broken controls

Verified dead or misleading paths:

- Change History does not include the current durable workflow.
- Validation rejection says to fix/revalidate but provides only Cancel.
- Warnings & failures can say none when an apply error exists.
- Images overall coverage tile is a button without an action.
- Missing-media search gives no empty-result feedback.
- Images Clear filters breaks visible model scoping.
- Wildcard-conflict action is labeled as a presentation edit rather than a conflict resolution.
- Backend structure-table editors exist as schemas but have no reachable frontend.
- A no-dependent trash icon acts immediately rather than opening a confirmation.
- Advanced returns to Options after a draft save/delete, losing the current maintenance context.

Controls verified working:

- First-run workbook reload/import
- Global model selector and model cards
- Section filters and section detail close
- Connected search and entity links
- Named diagnostics
- Option and group editors
- Group-member controls
- Raw table search and pagination
- Image status/coverage/section/type/intent filters
- Image pagination
- Safe image proposal save
- Review links into draft-added options
- Commit, preview, approve, typed apply, retry, cancel, and new draft
- Comparison export
- Backup
- Status refresh
- Re-import after apply

## 7. UX, copy, and navigation issues

Most likely to confuse a competent first-time user:

- “Change History (append-only audit)” is authoritative-sounding but excludes actual Manager applies.
- “Fix the reported problems, then revalidate” describes an unavailable action.
- “No recorded warnings or failures” can contradict the apply state.
- Every mixed-draft entity can show the same draft-wide model list.
- Images can display one model globally and another model in the inbox.
- “Read-only connected view” is shown on pages that contain edit actions; the intended distinction is base projection versus draft editing, but the label is not immediately clear.
- Search is a combined direct/mention/relationship search without explaining result classes or why apparently unrelated options appear.
- Groups requires the user to know a search term; it has no discoverable list or counts.
- Technical identifiers dominate Images coverage cards and section filters.
- Unmatched media uses an 837-option native select.
- Draft-effective values are not consistently reflected in the detail view.
- Advanced is a large raw-table maintenance surface with icon-only row actions and poor narrow-screen containment.
- First-run presents the same Reload Latest Workbook Data action in both the readiness banner and startup panel.

## 8. Workbook data or operations missing from the Manager

Still requiring manual workbook editing

- Context choice copy and tooltip authoring
- PriceRef rows
- Runtime rule exceptions
- Rule phrase mappings
- Runtime promotion metadata
- Workbook source-role/sheet registration
- Variant definitions
- Model-variant membership
- Order-summary section definitions
- Step-to-summary mappings
- Creating or deleting models
- Creating or deleting runtime steps
- Creating or deleting context sections
- Deleting section-presentation rows

Manageable only through raw, high-friction workflows

- New option plus OVS coverage
- Large option/group deletion graphs
- Rule mappings
- Price rules
- Variant overrides
- Default rules
- Interior hierarchy/scope/components
- Color overrides
- Many asset-map ownership/conflict corrections

Indirectly managed rather than directly authored

- Generated contracts
- Published data.js
- Browser cache version
- Form graph placement derived from several tables
- Image reconciliation proposals
- Generated-artifact/publication freshness

## 9. Prioritized remediation backlog

### P0

No confirmed Critical/P0 defect was found. The guarded writer did not corrupt the workbook; failed downstream work restored the original hash, and the complete pipeline succeeded once the isolated output baseline was valid.

### P1 — required before treating the Manager as the primary workbook authority

1. Replace the legacy Change History panel with current durable draft/apply history.
2. Add reachable editors for promotion, source routing, variants/membership, and summary mappings.
3. Add a correction/fork/discard workflow for mutable and rejected drafts.
4. Surface apply-attempt errors directly and fix the false “No recorded warnings or failures” state.
5. Render per-entity affected-model scope.
6. Eliminate Images model-header/filter desynchronization.

### P2 — required for dependable daily maintenance

1. Add guided option creation with OVS coverage.
2. Add coordinated dependency-delete planning and bulk drafting.
3. Add confirmation/Undo for immediate raw deletes.
4. Preserve Advanced collection/search/page state after draft saves.
5. Add searchable/paged unmatched-media target selection.
6. Add explicit no-results and API-error feedback to media search.
7. Clarify or implement wildcard-conflict resolution.
8. Render draft-effective values in connected detail views.
9. Add direct management for the four currently unprojected workbook sheets where appropriate.

### P3 — usability and polish

1. Add a Groups browse/index mode.
2. Distinguish direct search matches from descriptive mentions and relationships.
3. Make diagnostics a separate result state.
4. Clear irrelevant query parameters when switching workspaces.
5. Improve human labels for section IDs and raw technical fields.
6. Contain Advanced tables and toolbars on narrow screens.
7. Remove or activate the dead overall coverage button.
8. Consolidate duplicate first-run reload actions and standardize lifecycle naming.

## Direct answers

### What can it actually do today?

Import and verify the workbook; browse six models; edit most options, availability, groups, rules, pricing, defaults, interiors, scopes, components, overrides, and assets; maintain group membership; resolve many image cases; persist durable drafts; validate, approve, write, rebuild, publish, roll back, export, back up, and re-import.

### What visible functionality is broken or incomplete?

Current Change History, rejected-draft correction, apply-error presentation, per-change model scope, Images clear-filter scoping, several image triage controls, coordinated graph operations, and Advanced workflow continuity.

### What edits fail to persist correctly?

No representative field edit was lost. Option and asset edits persisted in the draft, and the option update persisted through workbook write and re-import. The main persistence-related defect is that successfully applied work does not appear in the visible History panel.

### What workbook data is missing or inaccessible?

Four sheets are entirely unrepresented, and six key structure areas are read-only or indirect despite writable backend schemas.

### What still requires manual workbook editing?

Promotion, source routing, variants/membership, summary definitions/mappings, context-choice copy, PriceRef, runtime exceptions, rule phrases, and structural create/delete operations.

### What is likely to confuse a first-time user?

The misleading History panel, impossible “fix and revalidate” instruction, hidden apply errors, incorrect affected-model labels, model-scope mismatch in Images, search-result breadth, search-only Groups navigation, raw identifiers, and the enormous unmatched-media selector.

### Highest-priority completeness gaps?

A trustworthy audit/history surface, full structure-table management, correctable drafts, accurate scope/error reporting, and coordinated option/dependency workflows.

## Audit integrity

- The repository’s canonical workbook remained at its starting hash.
- The repository retained the same seven pre-existing modified files; I added no tracked changes.
- git diff --check passed.
- No automated test suite was run because this was a no-change functional audit; actual browser/API/disk behavior was the primary evidence.
- The isolated server was shut down after the audit.
- Branch: feat/images-workspace-parity; its configured upstream currently reports [gone].
- Commit/PR: none, as requested.
