# Canonical-row compiler and exception queue — production design

Status: Direction approved 2026-07-09. Milestone 0 safety closure was implemented and proved on 2026-07-09. Milestone 1 headless compilation, Milestone 2's read-only compiler/typed-exception browser flow, and Milestone 2.1 compiler-consumer closure were implemented and independently verified on 2026-07-13. Milestone 2.2 typed endpoint, Color/Trim, and metadata profile compilation was implemented with fresh parent proof on 2026-07-14 and is pending independent closeout. Milestone 3 plan projection, workbook write, runtime publication, and model promotion remain unapproved. Reasoning level for implementation: high.

## 0. Decision summary

The production ingest wizard will stop asking the user to manufacture a complete workbook through broad review lanes.

The script will compile every target fact that is deterministically supported by the raw import, the canonical workbook contract, and safe target-workbook reconciliation. The user will see only a typed exception queue for facts the script cannot derive without product judgment.

Comparator-model relationships become a first-class evidence layer. They may corroborate a target interpretation, reveal a likely missing relationship, and prebuild a focused relationship or exclusive-group proposal. They may not independently establish a target-model fact, and comparator IDs, prices, copy, sections, defaults, or group names may never be copied into target rows.

Implementation is intentionally ordered:

1. Close the live-write safety gaps found after D.2.
2. Build the headless canonical-row compiler and comparator evidence index.
3. Replace broad decision lanes with the focused exception queue.
4. Project a ready canonical manifest into a mechanical apply plan.
5. Prove the full flow on a fresh run and stop at a deployment-ready dry-run report for a separate live-write approval.

This design does not approve `--write`, mutate `stingray_master.xlsx`, regenerate tracked runtime artifacts, publish `form-app/data.js`, or promote a model.

## 1. Goal and production definition

The goal is one clean path:

```text
raw order-guide import
  -> preserved source evidence
  -> canonical-row compiler
  -> focused exception resolutions
  -> complete canonical-row manifest
  -> mechanical workbook operation plan
  -> temporary-workbook proof
  -> separately approved safe workbook write
  -> existing generators
  -> existing registry/runtime
```

The ingest wizard is production-ready only when all of the following are true:

- Every in-scope raw feature has a recorded disposition: compiled, retained existing data, explicitly not a workbook fact, explicitly deferred under an allowed policy, or represented by an open exception.
- Every target canonical row has complete live-workbook headers, typed values, stable identity, target evidence, and a derivation record.
- Zero blocking exceptions remain before plan approval.
- Comparator facts loaded for the selected target/comparator pair have explicit dispositions; no comparator behavior leaks into the target silently.
- The desired target state reconciles with existing target rows without avoidable ID churn or unresolved dependent references.
- Every active option row writes explicit Boolean `selectable` and `active` values.
- The apply plan passes package, schema, Boolean-hygiene, cell-exact readback, generator, registry-discovery, and generated-contract checks on a temporary workbook before the live workbook is eligible for mutation.
- The normal browser flow asks the user only for non-derivable facts, with one focused action and a canonical-row preview per exception.
- Existing generators can translate the resulting workbook rows into clean runtime contracts without model-specific Python or JavaScript business exceptions.

Production readiness is evidence coverage, not a hardcoded requirement that a particular model have a nonzero count in every sheet. Zero rows are valid only when the source-feature ledger proves that zero is complete for that model and surface.

## 2. Diagnosis and current evidence

Change class: mixed ingest tooling, browser workflow, validation/tests, and later workbook/data application. Runtime and dealer behavior are verification surfaces, not implementation targets.

Risk level: high. This work controls the first canonical workbook write for new/reprocessed model data and feeds the customer-facing generator path.

### 2.1 D.2 proved mechanical execution, not write readiness

The D.2 run is `form-output/ingest-wizard/20260709-003524-650cae`.

Its 5,771-operation dry-run proved that the current batch can execute against a temporary workbook shape, but it also exposed the following blockers:

- `apply-plan.json` reports `valid=true` while ZR1 and ZR1X are `not_deployment_ready` with zero generated price rules and zero generated rule groups.
- The 546 planned option additions contain 350 rows with no `selectable` value, 196 with `selectable=False`, and none with `selectable=True`. The runtime treats a blank as display-only rather than a customer-selectable option.
- Reprocessing changes 340 matched existing option identities: 169 ZR1 IDs and 171 ZR1X IDs.
- The dry-run reports 22 referenced-delete warnings against `LZ_Interiors.included_option_id` and `color_overrides.option_id`.
- Dry-run `verification.checked` is zero. Post-write verification checks key presence/absence, not every planned field after workbook coercion.
- `apply_approved_plan()` computes deployment continuity after its call to `apply_batch(..., write=write)`. A live write can therefore happen before deployment readiness is known.
- The approval label says “D.2 dry-run only,” but that intent is free text. `plan-approval.json` has no machine-readable approval scope.
- The temporary probe activates `model_variants`; `promote_model.py` does not, even though generator discovery requires active model-membership rows.

These are safety-closure blockers. No compiler implementation may make the live writer easier to reach until they are closed.

### 2.2 The current review model asks the user to approve derived facts

The same D.2 run contains 1,028 saved decision records:

- 608 section decisions;
- 310 price decisions;
- 57 copy-split decisions;
- 23 relationship-lane records, of which 20 are relationship candidates;
- 15 exclusive-group decisions;
- 15 presentation row sets.

559 records were copied between models. That process can preserve a useful UI shortcut, but it does not prove that target-specific variants, presentation rows, rules, defaults, or scopes are correct. Deterministic rows should be compiler output, not synthetic reviewer decisions.

### 2.3 Comparator relationship data is useful but currently unused

The current relationship queue is driven by phrase hints from `wizard/hints.py`. It does not index comparator rule, rule-group, exclusive-group, default-selection, or price-rule sheets.

Read-only inspection of the live workbook found:

| Comparator | Direct rules | Rule groups | Exclusive groups | Price rules |
|---|---:|---:|---:|---:|
| Grand Sport | 124 | 28 | 12 | 51 |
| Z06 | 80 | 35 | 13 | 72 |

These are authored-row inventory counts. Exact comparator topology must later mirror the generator's row-level active filtering for groups and members; authored inactive members are not runtime-effective evidence.

RPO-normalized endpoint analysis also found meaningful overlap with the selected targets:

- GSX has both endpoints for 54 Grand Sport direct rules, all members for 17 rule groups, and all members for 9 exclusive groups.
- ZR1/ZR1X each have both endpoints for 21 Z06 direct rules, all members for 2 rule groups, and all members for 6 exclusive groups.

Endpoint overlap does not prove shared semantics, but it is strong evidence that the comparator can reduce manual work when combined with target raw clauses or target peer structure. The current flow discards that evidence and produces only 31 planned direct rule rows from 20 relationship records.

### 2.4 Relationship direction is not reliably owned by the current hint UI

The workbook-owned `rule_phrase_map` carries phrase direction and stop-phrase behavior. The current `hints.py` vocabulary duplicates phrase semantics, and the browser prefill treats the current candidate as the source.

For example:

```text
Raw CAV text: Included with (PEF)
Canonical edge: PEF includes CAV
Unsafe generic prefill: CAV includes PEF
```

The compiler must load and fingerprint active `rule_phrase_map` rows. Comparator topology may corroborate the result, but the workbook phrase direction determines the parse.

## 3. Source-of-truth and evidence boundaries

### 3.1 Target raw import

The raw import is authoritative for what the target order guide says: RPOs, descriptions/disclosures, status cells, variant headings, price cells, source grouping, and source coordinates.

The compiler may normalize and interpret explicit structure, but it must preserve the raw value and coordinate for every derived fact. Missing or ambiguous target evidence remains missing or ambiguous; it is never repaired by silently copying a comparator.

### 3.2 Existing target workbook rows

The canonical workbook is authoritative for the row contract and for already-established target identities and retained target data.

For ZR1/ZR1X, inactive scaffold contents remain non-canonical as product truth. Their existing IDs and incoming references are still operational facts that the reconciler must preserve or deliberately remap. “Non-canonical scaffold” is not permission to delete referenced identities wholesale.

### 3.3 Comparator workbook rows

The explicitly selected comparator is contextual evidence only.

Comparator rows may:

- corroborate a target-derived direct rule;
- show the canonical shape for a target clause;
- prefill a rule-group or exclusive-group proposal when target members/topology are present;
- identify a likely conditional-price question linked to a target relationship;
- increase confidence or expose a conflict.

Comparator rows may not:

- create a ready target rule without target evidence or a typed reviewer resolution;
- supply a target price value or default selection;
- transfer comparator `option_id`, `rule_id`, `group_id`, `price_rule_id`, section ID, display order, notes, disabled copy, or model-specific scope;
- prove the reverse or symmetric form of a rule;
- override explicit target raw evidence.

### 3.4 Canonical workbook rows

Only rows in a ready `canonical-row-manifest.json` are eligible for apply-plan projection. The manifest is transient evidence, not a second product source. After an approved write, the workbook rows are canonical and normal generator workflows resume.

### 3.5 Generated artifacts and runtime

`form-output/` runtime contracts and `form-app/data.js` remain generated outputs. They are never edited to compensate for ingest gaps. Runtime JavaScript and dealer-submission behavior remain unchanged unless a later, separate, evidence-backed spec proves a generic runtime defect.

## 4. Design principles

1. **Compile what is derivable.** Exact source facts and mechanical workbook translation do not need user approval.
2. **Ask only focused questions.** Each user interaction supplies one missing fact or resolves one explicit conflict.
3. **Desired state before operations.** First construct complete canonical rows, then reconcile them against the workbook, then project editor operations.
4. **Evidence before confidence.** Confidence labels summarize evidence; they never replace deterministic gates.
5. **Comparator as corroboration, never authority.** Exact comparator agreement can strengthen or prefill, not invent.
6. **Stable semantic identity.** Reprocessing should update/no-op matched rows, not delete and renumber them.
7. **No silent gaps.** Every raw relationship/price/status feature and every applicable comparator fact receives a disposition.
8. **Readiness before mutation.** All write-eligibility work happens on a temporary workbook before a live save.
9. **One workbook-to-runtime path.** The existing generators remain the proof that compiled rows are canonical.
10. **No model-specific business exceptions in code.** Model differences come from source evidence, workbook metadata, and typed resolutions.

## 5. Milestone 0 — mandatory safety closure

Safety closure is an independently testable implementation milestone and a prerequisite for compiler work reaching the apply path. It must not write the live workbook.

Milestone 0 closes the writer by detecting and refusing every unsafe condition in the current plan; it does not pretend to repair non-derivable option flags, identity churn, or references before compiler artifacts exist. The later compiler/reconciler must produce a compliant `pass-c-3` plan, but it cannot weaken or bypass these writer-level refusals.

### 5.1 Explicit option semantics

Every emitted option row must contain typed Boolean values:

- normal orderable customer choice: `selectable=True`, `active=True`;
- display/reference-only choice: `selectable=False` with its explicit display behavior;
- intentionally inactive row: explicit `active=False` and explicit `selectable` value.

For a pre-`pass-c-3` diagnostic plan, blank `selectable` or `active` may pass `dry_run_evidence` approval so the unsafe plan can be diagnosed, but it blocks `writeEligibility`, creation of `write-approval.json`, and live write. In `pass-c-3`, a blank means the canonical manifest is not ready and blocks plan creation/approval. The compiler may not rely on runtime fallback semantics.

### 5.2 Stable identity and desired-state reconciliation

The current clean-reprocess delete/re-add strategy is replaced for production planning.

The compiler-owned identity reconciler (`identity.py`) must:

- match a unique existing target option by `(model, normalized RPO, occurrence identity)`;
- reuse its existing `option_id` and emit `update` or `noop` as appropriate;
- reconcile OVS rows by `(option_id, variant_id)`;
- treat context-distinct duplicate RPOs as separate occurrence identities derived from target source context;
- turn an ambiguous existing match into a blocking exception rather than allocate a new ID;
- allocate a deterministic new ID only for a genuinely new semantic row;
- keep every existing workbook ID reserved even when its row is approved for deletion, so a retired identity is never recycled for a different semantic row;
- reuse existing direct-rule, group, exclusive-group, price-rule, and default-rule IDs when their semantic signatures match;
- generate new IDs deterministically from the target semantic signature, never from comparator keys or iteration order.

No target family is cleared wholesale. An unmatched existing row is retained unless the source proves removal or the user resolves a typed retention/removal exception.

### 5.3 Incoming-reference closure

Before planning any option deletion or identity remap, build a complete incoming-reference graph across all registered canonical families and global dependents.

At minimum this includes:

- direct rule source/target IDs, whose target-owned entity type may be option or interior under the existing generator contract;
- rule-group source/member IDs;
- exclusive-group member IDs;
- price-rule condition/target IDs, also validated against the generator's typed option-or-interior entity universe;
- `default_selection_rules.target_option_id` and condition-type-aware `condition_id` references: blank for `always`, RPO for `unless_selected_rpo`, section ID for `unless_selected_section`, and option ID for `when_selected_unless_selected_section`;
- variant overrides;
- interior `included_option_id` and related option fields;
- `model_interior_scope.requires_option_id` resolved within the row's `model_key` option universe;
- `color_overrides.option_id` and the legacy-named `color_overrides.adds_rpo`, both of which contain option IDs in the current generator contract;
- `asset_map.target_id` only when `target_type == "option"`; other target types retain their own typed identity;
- any other option-reference columns registered by the live workbook schema.

`editor_ops.py` must extend `EDITOR_SHEET_META`/`GLOBAL_SHEET_FAMILIES`, support the existing option-or-interior union references used by rules/prices, and add condition-type-aware validators for currently unregistered global references rather than relying on column-name guessing. `asset_map` joins the global-family registry with its conditional target semantics; `interior_components` is registered for canonical apply even though it has no option-ID reference today. An unresolved referenced delete is an unconfirmable blocker. `--confirm-plan-warnings` may not override a `refdel:` condition. A deletion proceeds only when every surviving reference is retained, removed, or remapped in the same final-state plan.

### 5.4 Structured approval scope

Approval uses two separate records so dry-run intent is never overwritten or confused with write authority:

- `plan-approval.json`, schema `plan-approval-2`, scope `dry_run_evidence`;
- `write-approval.json`, schema `write-approval-1`, scope `deployment_ready_write`.

Only `pass-c-3` plus both current approval schemas can ever be writable. Every `pass-c-1`/`pass-c-2` plan and historical approval, including D.2, is permanently dry-run-only regardless of its label or the current code's older write rule.

A plan approval can never authorize `--write`. The separate deployment-ready write approval binds:

- run and exact target set;
- plan SHA;
- canonical-manifest SHA;
- compile-report SHA;
- exception-resolution SHA;
- eligible dry-run report SHA;
- workbook fingerprint;
- explicitly accepted confirmable warning IDs;
- explicitly allowed nonblocking deferrals.

The production wizard does not offer a non-deployment scaffold write. If that capability is ever needed, it requires a separate spec, a separate approval scope, and an explicit non-production CLI flag.

During Milestone 0, only `plan-approval.json` is issuable because `pass-c-3` and compiler artifacts do not yet exist. The server must refuse creation of `write-approval.json` until the bound `pass-c-3` plan and eligible dry-run report exist.

### 5.5 Pre-write temporary-workbook proof

The two approval paths are ordered explicitly.

Dry-run proof:

1. Build `pass-c-3` from a ready manifest. During Milestone 0, the historical/current plan may still be dry-run for diagnostics, but it is categorically non-writable.
2. Record `dry_run_evidence` approval bound to the current available inputs. Compiler hashes are required once compiler artifacts exist and are omitted, not faked, for the Milestone 0 diagnostic path.
3. Verify source, target selection, comparator/phrase-map when present, manifest/resolution when present, plan, dry-run approval, workbook mtime, and workbook SHA fingerprints.
4. Refuse an Excel lock file.
5. Copy the current workbook to a temporary path.
6. Apply the exact prepared operation batch to the temporary workbook through the same editor/writer path used for the live file.
7. Reopen the saved temporary workbook and perform exact readback.
8. Run workbook package, schema, and Boolean-hygiene validation.
9. For `pass-c-3`, activate the target only in the scratch copy, run existing model discovery/generation, and compare generated contracts with manifest signatures/source-feature coverage.
10. Emit `writeEligibility`; for an atomic multi-target plan, every selected target must be eligible or top-level `eligible` is false.

Live apply:

1. Permit creation of `deployment_ready_write` approval only after a `pass-c-3` dry-run report has `ok=true`, `status=validated_write_eligible`, and `writeEligibility.eligible=true`.
2. Bind that approval to the eligible report SHA and all inputs listed in §5.4.
3. On `--write`, require `pass-c-3`, `plan-approval-2`, `write-approval-1`, `deployment_ready_write`, schema validation enabled, and exact hash/warning/workbook agreement.
4. Repeat fingerprint, warning, lock, eligibility, and workbook-refusal checks before the first live mutation.

`write=True` with schema validation disabled is a service-level refusal even if the CLI is bypassed. `--no-schema-validation` remains fixture/debug dry-run-only.

### 5.6 Exact readback

`editor_ops.apply_batch()` may coalesce raw operations, so readback is defined against its prepared operation list while preserving complete raw-operation coverage:

- created sheet and exact headers exist;
- each added/updated row exists under its canonical key;
- every planned field equals the saved cell value after approved coercion;
- each deleted row is absent;
- every raw plan operation maps to a prepared operation/effect, with no dropped or contradictory raw operation;
- `rawCovered == combinedRawOperationCount`;
- `preparedChecked == preparedOperationCount`;
- any mismatch produces `readback_failed` and blocks write eligibility.

The same exact readback runs after a safe live save. A mismatch moves the session to `apply_verification_failed`, preserves the backup and failure report, blocks blind retry, and requires an explicit restore or reconciliation pass before further apply work. It must not mark the session applied.

### 5.7 Promotion activation parity

`promote_model.py` must activate and verify the target's `model_variants.active` membership rows in addition to `model_master`, `variant_master`, and registry-promotion metadata. On-disk verification must prove that `discover_generation_model_configs()` discovers the promoted target.

This change is tooling parity only. Actual model promotion remains a separate explicit action after canonical workbook and generator gates pass.

### 5.8 Report and refusal contract

`plan.valid` continues to mean structurally valid; it must not imply deployment or write readiness.

The apply report adds:

```json
{
  "status": "validated_write_eligible | validated_write_blocked",
  "writeEligibility": {
    "eligible": false,
    "blockers": [],
    "deferrals": []
  },
  "liveWriteBlockedReason": "..."
}
```

`--write` stops before mutation if any of these is true:

- `write-approval.json` is absent or its scope is not `deployment_ready_write`;
- plan schema is not `pass-c-3`, plan approval schema is not `plan-approval-2`, or write approval schema is not `write-approval-1`;
- any bound hash or fingerprint is stale;
- Excel lock or workbook mtime drift exists;
- schema validation is disabled;
- an emitted option has blank `selectable` or `active`;
- semantic identity is ambiguous;
- a referenced delete is unresolved;
- an unknown/non-allowlisted warning remains or the approved warning set drifted;
- temporary apply, package, schema, Boolean, or cell-readback validation fails;
- target discovery/generation fails;
- generated validation errors remain;
- any compile or deployment blocker remains.

A blocked write attempt leaves the workbook byte-identical and does not overwrite the last successful dry-run report or create `apply-report.json`.

A successful but ineligible dry-run returns `ok=true`, `status=validated_write_blocked`, and process exit zero because the requested evidence run completed. An ineligible `--write` returns `ok=false`, exits nonzero, and never mutates the workbook. An already-applied run is never replayable.

The initial finite writer policy is `editor_ops.CONFIRMABLE_WARNING_KINDS = {"scaffold"}`. A `scaffold:` warning is confirmable only for a selected target sheet intentionally left inactive pending separate promotion and only after its scratch activation/generation probe passes. `dorder:` collisions, `refdel:`, unknown kinds, newly appearing warnings, and warning drift are write blockers. A write approval binds the exact accepted scaffold warning IDs and a warning-set fingerprint; the blanket live behavior of `--confirm-plan-warnings` is retired.

## 6. Canonical-row compiler contract

### 6.1 Inputs

The compiler consumes only fingerprinted inputs:

- Pass A source evidence and parsed candidates;
- selected primary and comparator models;
- target/comparator workbook snapshot and active source-role registrations;
- live canonical headers and metadata, including `section_master` and `rule_phrase_map`;
- target existing-row state and incoming-reference graph;
- typed exception resolutions from the same subject fingerprints.

The D.2 run remains immutable historical evidence. Production proof uses a fresh run. Existing `decisions.json` records are not silently promoted into compiler truth; any reusable non-copied choice must pass a one-time migration validator and appear as a proposed exception resolution bound to current evidence.

### 6.2 Output families

The compiler emits complete desired canonical rows for every registered generator role and relevant shared surface:

| Family | Canonical destination | Automatic basis | Exception trigger |
|---|---|---|---|
| Model metadata | `model_master`, `model_workbook_sources`, `model_variants`, `variant_master`, `model_registry_promotion` | selected target, live headers, parsed variant matrix | target label/year/variant conflict |
| Options | target `*_options` | raw RPO/copy/price, section evidence, explicit flags | duplicate identity, unresolved section/copy/price |
| Status | target `*_ovs` | parsed target status matrix | unknown symbol, variant mismatch |
| Direct relationships | target `*_rule_mapping` | direction-aware explicit target clause | ambiguous direction/endpoints/scope/conflict |
| Rule groups | target `*_rule_groups` + members | explicit grouped target semantics, optionally comparator-corroborated | partial set or unclear group type |
| Exclusive groups | target `*_exclusive_groups` + members | explicit target peer/selection evidence, optionally comparator-corroborated | comparator-only or incomplete peer set |
| Price rules | target `*_price_rules` | target conditional price evidence | value/scope/condition not derivable |
| Defaults | `default_selection_rules` | explicit target default evidence | comparator-only or missing target default |
| Variant overrides | optional target override sheet | target variant-specific evidence | unresolved variant override |
| Interior/color | registered interior source, `model_interior_scope`, `interior_components`, `color_overrides` | exact target identities and existing canonical scope | non-option identity or source not parsed |
| Presentation | `runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, `step_order_summary_map` | workbook-owned reusable structure validated for target sections | target-specific difference or no reusable profile |
| Media | `asset_map` | exact retained/new target option identity when source exists | permitted explicit deferral if media is absent |

Required generator-role coverage comes from `model_configs.py`, not a duplicated list hidden in the UI. Optional/unsupported source families remain visible in the compile report; they are never silently dropped.

### 6.3 Derivation records

Each row carries a transient derivation record:

- stable derivation ID;
- target model and canonical family;
- raw evidence references and coordinates;
- workbook metadata/schema references;
- comparator evidence references, if any;
- phrase-map rule and direction, if any;
- typed exception resolution reference, if any;
- normalized semantic signature;
- derivation rule/version;
- disposition and status.

Provenance remains in run artifacts. This design adds no provenance columns to canonical workbook sheets.

### 6.4 Source-feature ledger

Every extracted feature receives exactly one disposition:

- `compiled`
- `retained_existing`
- `exception_open`
- `resolved_not_a_workbook_fact`
- `resolved_not_applicable`
- `allowed_deferral`
- `unsupported_blocker`

Relationship phrase hits, price conditions, status symbols, group candidates, and applicable comparator facts may not disappear between parsing and planning. The compile report fails on an unclassified feature.

### 6.5 Desired state and mechanical projection

The compiler's `identity.py` owns existing-row matching, stable workbook ID reuse/allocation, desired-versus-existing diffing, incoming-reference impact, and the final `add`/`update`/`delete`/`noop` action stored in the manifest.

`plan_builder.py` stops inferring product meaning or reconciling identity. It receives a ready, already-reconciled canonical manifest and performs only:

- live-header validation;
- conversion of each manifest action to the corresponding editor operation without changing keys or values;
- dependency ordering;
- coverage and fingerprint projection into `apply-plan.json`.

If plan projection would need to choose an ID, match an existing row, change a field, or alter an action, it fails and returns the manifest to the compiler.

The next plan schema is `pass-c-3`. It binds the canonical manifest, compile report, exception resolutions, comparator evidence, phrase-map, and workbook fingerprints.

### 6.6 Core raw-to-canonical contracts

These four translations are part of the compiler contract, not open-ended reviewer work.

#### Sections and display order

Section derivation uses this order:

1. A uniquely matched existing target occurrence retains its canonical `section_id` when that section still exists and the target raw role does not contradict it.
2. Otherwise, exact occurrence-level RPO precedent may supply the section only when at least two independent active non-target model occurrences agree and the target's confirmed raw sheet role is compatible. The selected comparator may be one corroborating precedent but cannot be the sole source. A lone comparator precedent produces a prefilled section exception; any conflicting active precedent prevents auto-derivation.
3. If the source provides an explicit heading that resolves to one live `section_master` row under workbook-owned naming/presentation metadata, use that section.
4. Any remaining ambiguity becomes one section exception with a finite candidate list derived from the live section/predecessor evidence. No hardcoded model section map is introduced.

Matched target rows retain display order unless the target raw evidence explicitly supplies a changed order. New rows receive deterministic section-local order from the target source sequence with normalized RPO/occurrence signature as the tie-breaker. Source coordinates may influence presentation order, but never durable identity. Comparator display order is never copied.

#### Price Schedule rows

Every in-scope Price Schedule row receives a ledger disposition.

- An exact uniform price keyed by target RPO and applicable target model scope becomes the option's base `price`.
- A scoped/conditional row becomes a `price_rules` `override` only when the target row explicitly resolves: target RPO, condition RPO (or self-condition for a trim-scoped target), numeric value, body scope, and trim scope.
- Condition/target RPOs resolve to target option IDs after target identity reconciliation.
- Variant headers normalize body/trim qualifiers through the target variant matrix; no comparator scope is copied.
- A repeated RPO with conflicting values, prose-only qualifier, missing condition, or unresolved scope becomes a typed price exception.
- A zero override for an included component requires target evidence of no additional charge. Comparator zero rules may prefill the question but do not supply the value.

#### Variants and base model rows

Variant semantic identity is `(model_key, normalized trim_level, normalized body_style)`.

1. Reuse an exact existing target `variant_master.variant_id` when its model/trim/body semantics match the parsed target header.
2. If no row exists, derive a candidate ID only through the canonical variant-ID convention after a validator proves that convention against active workbook rows. Otherwise create a blocking variant-ID exception.
3. A complete new `variant_master` row requires target-derived `model_year`, `trim_level`, `body_style`, display name, exact Price Schedule base price, deterministic display order, and explicit `active=False` until promotion.
4. `model_variants` membership reuses the same ID and remains explicitly inactive until promotion.
5. Missing/ambiguous year, body, trim, label, or base price blocks the variant row; comparator variants never fill those fields.

#### Duplicate-RPO occurrence identity

A unique target RPO uses `(model_key, normalized RPO)` identity. Duplicate RPOs add a durable occurrence signature built from canonical semantics, not source coordinates:

- orderable versus reference-only role;
- resolved canonical section;
- normalized customer copy identity;
- variant status vector keyed by variant semantic identity;
- base/conditional price signature;
- relationship/group role where it distinguishes occurrences.

The signature excludes sheet name, row number, source order, display order, comparator IDs, and timestamps.

Existing rows without source provenance are matched in deterministic stages: exact full occurrence signature; then exact RPO + section + status vector + price signature (allowing copy to be updated); then a unique one-to-one remaining occurrence for that RPO. If any stage yields more than one valid match, emit a duplicate-identity exception. Never use fuzzy text scoring to choose an ID.

## 7. Comparator relationship evidence

### 7.1 Loading and normalization

Load only the comparator selected in `model-selection.json` and only its active `model_workbook_sources` roles. Inactive ZR1/ZR1X scaffolds are never eligible comparator truth.

Mirror the existing generator loaders rather than inventing broader topology:

- rule-group and exclusive-group facts include only active groups and active members;
- direct-rule and price-rule sheets have no row-level `active` field, so structurally valid rows are indexed, while endpoint activity is retained in evidence;
- an inactive option/member cannot silently expand the runtime-effective comparator group;
- non-option comparator endpoints such as interior identities receive `context_only_nonportable_entity` because cross-model interior identity is not portable. This does not prevent a target-derived, typed interior relationship from compiling from target Color/Trim/interior evidence.

Resolve comparator workbook IDs back to normalized RPO identity plus comparator occurrence evidence through the comparator's option source. Compare RPO semantics across models; never compare or transfer option IDs. Target occurrence identity is resolved independently from target evidence under §6.6. Comparator section, status, and price remain context and are never equality requirements for target identity. A comparator fact is exact only when its referenced RPO is unique among runtime-active comparator option occurrences; multiple active comparator occurrences make it ambiguous context. The index still retains inactive/duplicate occurrences so an active and inactive T0E can never be collapsed into one fact.

Blank scopes normalize consistently to `*`. Member order is irrelevant; duplicate or unresolved members invalidate an exact group match.

### 7.2 Evidence ladder

| Tier | Target evidence | Comparator evidence | Compiler result |
|---|---|---|---|
| A | Explicit clause/set, unique direction/endpoints/scope | Exact normalized match | Auto-compile; record comparator corroboration |
| B | Explicit clause/set, unique direction/endpoints/scope | No match | Auto-compile as target-derived; comparator absence is not negative evidence |
| C | Target statement is present but one mechanical shape is ambiguous | One unique exact comparator topology and no conflict | Auto-compile only if the comparator resolves a mechanical representation, not a missing product fact; otherwise prefilled exception |
| D | No explicit target rule, but all endpoints/peers exist and target structure independently makes the comparator fact plausible | Exact comparator topology | One focused confirmation/edit exception with complete proposed rows; no ready row before resolution |
| Context only | Comparator fact lacks target endpoints or target structural support | Any | Report as not applicable/context; no row and no routine user task |
| Target differs | Target evidence is explicit and unambiguous but comparator differs | Any | Compile the target fact; mark comparator `not_applicable_target_diff` and do not let it veto target evidence |
| Conflict | Target evidence is ambiguous/internally conflicting and comparator also disagrees or has multiple possible matches | Any | Blocking conflict exception; comparator cannot resolve the target ambiguity |

Tier D is how comparator data helps build relationships and exclusive groups without becoming target truth. It avoids asking the user to construct a group from scratch while still requiring confirmation when the raw target does not say the business rule directly.

### 7.3 Normalized semantic signatures

Direct rule:

```text
(rule_type, source_rpo, target_rpo,
 body_style_scope, runtime_action)
```

Rule group:

```text
(group_type, source_rpo, frozenset(member_rpos),
 body_style_scope, trim_level_scope, variant_scope)
```

Exclusive group:

```text
(selection_mode, frozenset(member_rpos))
```

Default selection:

```text
(target_rpo, condition_type, resolved_condition_rpo_or_section,
 body_style_scope, trim_level_scope, variant_scope, priority, display_behavior)
```

Price rule:

```text
(condition_rpo, price_rule_type, target_rpo,
 body_style_scope, trim_level_scope)
```

Price values are compared separately and never copied. Comparator section IDs may corroborate target structure but are not part of a portable target fact.

### 7.4 Surface-specific rules

Direct rules:

- Direction comes from active `rule_phrase_map` plus target syntax.
- Explicit target phrases with resolved product RPO endpoints may compile without comparator support.
- Missing comparator behavior never disproves a target rule.
- An explicit target rule that differs from the comparator compiles from target evidence and records the comparator as not applicable; only target ambiguity can block.

Rule groups:

- Auto-compilation requires target evidence of grouped semantics such as requires-any or excludes-any.
- A comparator may provide the canonical grouping shape and a proposed full member set.
- A comparator subset/superset or scope mismatch is not exact. It becomes an exception only when the target member set/scope is ambiguous; an explicit complete target set compiles and records comparator disposition `not_applicable_target_diff`.

Exclusive groups:

- Target evidence must independently support a peer set or selection behavior.
- Exact comparator topology can prefill one group-level confirmation card.
- Comparator-only membership never silently creates an exclusive group.
- `required_single_within_group` is never inferred from `single_within_group` or vice versa.

Defaults:

- Comparator defaults are context only because they encode model-specific runtime intent.
- A target default needs explicit target evidence or a typed user resolution.
- Priority remains part of the runtime-significant target/default signature even though comparator defaults never auto-author a target row.

Price rules:

- Comparator relationships can identify a likely zero-override or conditional-price question.
- The target price value and scope must come from target evidence or a typed resolution.
- An “includes” relationship and an exact comparator zero override may prefill the question; it may not copy the zero automatically unless target evidence independently proves no additional charge.
- A comparator price difference is expected nonportable context, not a target/comparator conflict.

Replacement semantics:

- A target `replaces` clause may compile only when an active workbook-owned phrase-map rule defines its direction and canonical representation.
- Without that phrase metadata, emit a typed relationship exception. Comparator use of `excludes` plus `runtime_action=replace` may prefill the representation but may not choose it silently.

### 7.5 Negative guards

- Exact RPO identity only; no fuzzy name, description, or section matching.
- Every emitted endpoint must resolve within the target planned/retained option universe.
- No implicit reverse rules or symmetric exclusions.
- No partial-group auto-acceptance.
- No comparator price/default/copy/ID transfer.
- No exact RPO-only match when the comparator or target has multiple occurrences.
- Non-option comparator endpoints receive an explicit context-only disposition rather than an unresolved error or silent drop.
- No cross-model bulk copying of relationship, group, exclusive, default, price-rule, or presentation resolutions.
- A comparator change may alter context/confidence; it may not alter an unambiguous target-derived row.
- Comparator and `rule_phrase_map` fingerprints invalidate affected derivations/resolutions when changed.

## 8. Exception queue contract

### 8.1 What belongs in the queue

The queue contains only non-derivable facts or conflicts:

- ambiguous sheet role or target variant identity;
- duplicate/context-distinct RPO identity;
- unresolved section or copy split;
- missing/ambiguous base price;
- unresolved conditional price rule;
- unknown target status symbol;
- unresolved relationship direction, endpoint, or scope;
- comparator-backed relationship confirmation;
- partial/ambiguous rule group;
- comparator-backed exclusive-group confirmation;
- target/comparator conflict;
- existing-row retention/removal choice;
- dependent-reference remap;
- target-specific presentation difference;
- explicitly permitted unsupported-source deferral.

No candidate receives a decision record merely because the compiler handled it successfully.

### 8.2 Focused actions

Each exception declares its allowed typed actions. Examples:

- choose one section/value/variant from a finite list;
- confirm or edit prebuilt relationship rows;
- confirm/edit the proposed group member set and selection mode;
- mark text as not a workbook rule with a required reason;
- mark a comparator fact not applicable to the target;
- retain an existing row;
- approve removal only after the reference-impact preview is empty or fully remapped;
- provide the exact missing price/scope;
- record an allowed deferral with its gate impact;
- leave unresolved, which blocks the corresponding readiness level.

There is no generic Approve/Skip control and no raw JSON input. The user sees the exact canonical rows that their action would enable before saving it.

### 8.3 Identity and lifecycle

`subjectId` is stable across evidence revisions and is deterministic from target model, exception type, and affected semantic identities. `exceptionId` is stable for that subject. A separate `subjectVersion` hashes only that subject's sorted stable raw/workbook/comparator/phrase-map evidence dependencies plus compiler policy/schema version; it does not hash the run-wide authority envelope.

Lifecycle:

```text
open -> resolved -> consumed by recompile
                    |-> ready canonical row(s)
                    |-> explicit non-rule/non-applicable disposition
                    |-> allowed deferral
                    `-> stale evidence -> reopen
```

A resolution records reviewer, time, typed payload, `subjectId`, `subjectVersion`, and evidence references in `exception-resolutions.json` and append-only `exception-log.jsonl`.

If a listed evidence dependency or the proposed canonical shape changes while the semantic subject remains the same, `subjectVersion` changes, the old resolution becomes stale, and the same exception reopens. An unrelated evidence or run-authority change triggers a coherent artifact rebuild but leaves the unaffected `subjectVersion` and matching resolution valid. If the semantic subject itself changes, the old exception is closed as `superseded` and links to a new `exceptionId`. A resolution is never copied to another model; the compiler may independently reach the same result from equivalent evidence.

### 8.4 Grouped review without hidden bulk copying

The UI may group exceptions that share the same type and proposed action, but selection is explicit, row/group previews remain visible, and each affected exception receives its own audited resolution. “Apply to all models” is not offered for product rules.

### 8.5 Closed deferral policy

The only currently allowed nonblocking deployment deferral is:

- `asset_map_media_missing` — model/option media may use the already-approved placeholder path and be filled through later routine workbook edits.

This allowlist is machine-enforced and versioned with the compile policy. Adding another kind requires a new approved spec; a reviewer cannot turn an arbitrary blocker into a deferral by changing a label.

Missing source that is proven not applicable is classified `resolved_not_applicable`, not deferred. Any applicable gap in options, OVS/status, section/selectability, variants/base prices, direct/group/exclusive/default/price rules, colors, interiors, interior components, presentation metadata, stable identity, or references remains a deployment blocker. A `deployment_ready_write` approval may list only allowlisted deferral IDs already present in the eligible compile report.

## 9. Run artifacts

### 9.1 `comparator-evidence.json`

Schema: `comparator-evidence-1`.

Contains:

- target/comparator pair and fingerprints;
- active comparator source-role sheet map;
- occurrence-aware RPO-normalized direct/group/exclusive/default/price facts using runtime-equivalent active group/member semantics;
- stable evidence IDs and source workbook row keys;
- target endpoint/member presence;
- endpoint entity type/activity and explicit context-only dispositions for nonportable entities;
- raw target evidence references, if any;
- normalized signature, match class, and final disposition.

### 9.2 `canonical-row-manifest.json`

Schema: `canonical-rows-1`.

Contains:

- all upstream fingerprints and compiler version;
- per-model mode: `greenfield` or `reprocess`;
- complete desired rows grouped by canonical family;
- row ID, target sheet, workbook key, complete typed values;
- semantic signature and stable identity match;
- desired action: `add`, `update`, `delete`, or `noop`;
- derivation/evidence references;
- incoming-reference impact;
- exception references;
- status: `ready`, `blocked`, or `suppressed`.

### 9.3 `exception-queue.json`

Schema: `exception-queue-1`.

Contains stable subject/exception IDs, current `subjectVersion`, supersession links, model/family/severity, reason codes, plain-language questions, allowed actions, proposed row previews, raw/comparator/workbook evidence, and gate impact.

### 9.4 `exception-resolutions.json` and `exception-log.jsonl`

The JSON file is current typed state; JSONL is the append-only audit trail. The resolution-file envelope binds the current queue fingerprint for coherent readback, while each resolution entry binds its own `subjectId` and `subjectVersion`. A changed queue envelope does not stale entries whose subject version is unchanged. Each JSONL event binds the subject/version and relevant queue fingerprint at the lifecycle transition.

### 9.5 `compile-report.json`

Schema: `compile-report-1`.

Contains:

- source-feature coverage by family and disposition;
- canonical row counts by model/family/action/status;
- comparator fact dispositions;
- exceptions by type/severity/state;
- incoming-reference impact;
- explicit `compileReady`, `planReady`, `writeReady`, and `deploymentReady` per model;
- exact blockers/deferrals with evidence IDs.

A single generic `valid=true` is insufficient.

### 9.6 `apply-plan.json`

Schema advances to `pass-c-3`. It contains only operations mechanically projected from a ready canonical manifest and binds all compiler/report/resolution fingerprints.

### 9.7 Approval records

- `plan-approval.json` (`plan-approval-2`) authorizes only temporary dry-run evidence for one exact plan/workbook/input fingerprint set.
- `write-approval.json` (`write-approval-1`) is created later, authorizes only deployment-ready live write, and binds the eligible dry-run report plus the exact warning/deferral sets.
- Approval history is appended to a run-scoped audit log; neither record is inferred from reviewer-name text.

## 10. Browser and API workflow

The forward browser wizard remains `scripts/ingest_wizard_server.py` plus `visualizer/ingest-wizard/`. The workbook editor's legacy Ingest Review tab remains debug/compatibility only and is not expanded into the production path.

### 10.1 User flow

1. Drop in or choose the raw file.
2. Review friendly sheet profiling and confirm sheet roles.
3. Select target and comparator models.
4. Compile.
5. See a summary: rows derived automatically, retained rows, exceptions needing the user, and blockers caused by missing source.
6. Resolve focused exceptions, with raw evidence, target workbook state, comparator context, and proposed canonical rows side by side.
7. Recompile until `compileReady=true`.
8. Review the canonical manifest/plan and record `dry_run_evidence` approval.
9. Run temporary-workbook proof and review its readiness report.
10. Only when the report is write-eligible, record a separate `deployment_ready_write` approval bound to that report.
11. Run the first live apply through the CLI after separate explicit approval; no browser write button is added initially.

Resume is a primary path: session listing/detail already exists in the backend and must become a visible “resume run” entry in the forward browser.

### 10.2 API additions

Use the existing `/api/wizard/sessions/<run-id>/...` convention:

- `POST .../compile`
- `GET .../compile`
- `GET .../exceptions`
- `POST .../exceptions/resolve`
- `POST .../exceptions/reopen`
- existing `POST .../plan` consumes only a ready manifest;
- existing `POST .../plan/approve` creates only `plan-approval-2` / `dry_run_evidence`;
- new `POST .../write/approve` creates `write-approval-1` only from an eligible bound dry-run report.

Legacy decision routes remain available only for historical/debug runs until a separate retirement pass.

### 10.3 Session states

The production path adds explicit states:

```text
models_selected
  -> compiled_with_exceptions
  -> compiled_ready
  -> plan_built
  -> dry_run_approved
  -> dry_run_validated_write_blocked | dry_run_validated_write_eligible
  -> write_approved
  -> applied | apply_verification_failed
```

Saving a resolution or changing any fingerprint invalidates downstream plan/dry-run/approval state.

## 11. Greenfield and reprocess behavior

### 11.1 Grand Sport X — greenfield proof

- Create missing target sheets from exact live canonical headers only.
- Build model metadata from selected target/variant evidence.
- Allocate deterministic target identities.
- Use Grand Sport only as comparator context.
- Never copy a Grand Sport row without target derivation or typed confirmation.
- Prove nonzero appropriate customer-selectable choices and complete feature coverage.

### 11.2 ZR1 — reprocess proof

- Match unique existing target RPO/occurrence identities and retain their option IDs.
- Emit updates/no-ops for matched rows and additions for genuinely new rows.
- Queue ambiguous duplicate matches and unmatched-existing retention/removal choices.
- Close all incoming references before deletion.
- Use Z06 as comparator context under the evidence ladder.
- Produce rules/groups/price rows from evidence coverage rather than hardcoded model-count checks.

### 11.3 ZR1X — repeatability proof

ZR1X uses the same reprocess implementation and comparator policy as ZR1. It is proof of generic repeatability, not a separate code path or model-specific exception.

## 12. Expected implementation surfaces

This is the expected scope for the later implementation plan. Exact edits may narrow after test-first characterization, but expansion requires review.

### 12.1 New modules

- `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py` — manifest schemas/validation.
- `scripts/corvette_form_generator/ingest/wizard/comparator_evidence.py` — active comparator index and normalized signatures.
- `scripts/corvette_form_generator/ingest/wizard/identity.py` — semantic matching, stable ID allocation, incoming references.
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py` — phrase-map parsing and direct/group/exclusive compilation.
- `scripts/corvette_form_generator/ingest/wizard/compiler.py` — orchestrates all canonical families and coverage.
- `scripts/corvette_form_generator/ingest/wizard/exceptions.py` — queue/resolution contracts and invalidation.

### 12.2 Existing tooling

- `scripts/corvette_form_generator/ingest/wizard/hints.py` — direction-aware evidence adapter or legacy wrapper; no duplicate phrase truth.
- `scripts/corvette_form_generator/ingest/wizard/decisions.py` — legacy compatibility/migration only on the production path; disable unsafe cross-model rule copying.
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` — purely mechanical canonical-manifest-to-operations projection; no identity matching or desired-state reconcile.
- `scripts/corvette_form_generator/ingest/wizard/session.py` — compiler/exceptions state, scoped approvals, pre-write readiness.
- `scripts/corvette_form_generator/editor_ops.py` — exact temp/readback and unconfirmable reference-delete enforcement where the generic writer owns it.
- `scripts/ingest_wizard_server.py` — compile/exception/readiness endpoints.
- `scripts/ingest_wizard_apply.py` — scoped approval/refusal contract.
- `scripts/promote_model.py` — `model_variants` activation/verification parity.
- `visualizer/ingest-wizard/index.html`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css`

### 12.3 Tests

New focused suites:

- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_comparator_evidence.py`
- `tests/test_ingest_wizard_relationship_compiler.py`
- `tests/test_ingest_wizard_exceptions.py`
- `tests/test_ingest_wizard_identity.py`
- `tests/test_promote_model.py`

Expected extensions:

- `tests/ingest_wizard_fixtures.py`
- `tests/test_ingest_wizard_hints.py`
- `tests/test_ingest_wizard_plan.py`
- `tests/test_ingest_wizard_apply.py`
- `tests/test_ingest_wizard_session.py`
- `tests/test_ingest_wizard_server.py`
- relevant wizard UI assertion suites;
- `tests/test_editor_ops_apply.py`
- `tests/test_editor_ops_global_families.py`
- `tests/test_registry_promotion_metadata.py`
- existing generator/contract gates selected by the README validation map.

### 12.4 Docs after implementation

- this design/status;
- `docs/ingest/README.md`;
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`;
- D.2 historical closure wording;
- `Order-Guide_IngestPrompt.md` only where its short route/guardrail pointers change;
- root `README.md` command/validation ownership only when commands or gates actually change.

## 13. Implementation milestones and review checkpoints

### Milestone 0 — safety closure

Implement the writer-containment portions of §5 against the current plan and prove:

- blank option flags are detected and block write eligibility;
- existing-ID churn is detected and blocks write eligibility;
- unresolved referenced deletes are unconfirmable blockers;
- cell-exact temp readback;
- readiness computed before mutation;
- dry-run approval rejected for write;
- all pre-`pass-c-3` plans/approvals are permanently non-writable;
- schema-disabled live apply, unknown warnings, warning drift, stale report SHA, mixed-target ineligibility, and already-applied replay are refused;
- model-variant promotion parity;
- live workbook unchanged.

The fresh report is expected to return `ok=true`, `status=validated_write_blocked`, with the current flag/identity/reference/product-data blockers enumerated. That is success for this milestone. `deployment_ready_write` approval remains impossible until Milestones 1–3 produce and prove `pass-c-3`.

### Milestone 1 — headless compiler and comparator evidence

Implement artifacts, feature coverage, identity reconciliation, phrase direction, comparator indexing, relationship compilation, and focused exception generation. Keep the live workbook untouched.

### Milestone 2 — exception queue browser flow

Replace broad review lanes in the forward wizard with compile summary, typed exception cards, recompile, resume, and readiness screens. Legacy debug routes remain.

Implemented 2026-07-13 under `milestone-2-exception-queue-browser-flow-implementation-plan.md`. The browser and API expose only actions that the current compiler can project to a complete canonical outcome; unsupported row-producing actions remain explicit source/tooling blockers rather than being recorded as resolved. The milestone remains read-only with respect to the canonical workbook, runtime publication, and promotion.

Milestone 2.1 closed the current action/consumer gap under `milestone-2-1-compiler-consumer-closure-implementation-plan.md`: status-bearing no-RPO standards compile canonically; exact identity, relationship, group, exclusive, price, default, and explicit no-row outcomes have consumers; comparator endpoints require one ready target identity; and GET/mutation projectability is identical.

Milestone 2.2 is implemented under `milestone-2-2-typed-endpoint-metadata-compiler-implementation-plan.md` with fresh parent proof pending independent closeout. Comparator selection now drives shared paint, LT/LZ interior, shared color-override, and presentation profiles; typed relationship catalogs distinguish options, interiors, and descriptive aliases. Fresh proof remains fail-closed at 374 subjects (257 actionable, 117 actionless). The 80 multi-interior one-of/group semantics and 37 incomplete comparator catalogs remain explicit tooling/catalog blockers, so Milestone 3 remains blocked and unapproved.

### Milestone 3 — mechanical plan and deployment proof

Project a ready manifest to `pass-c-3`, apply to a temporary workbook, run generator/registry/contract checks for GSX and ZR1, and repeat on ZR1X.

### Milestone 4 — fresh real-data closure

Run the full production path on a fresh all-target run. Review the manifest, exception audit, desired-state diff, and write-eligibility report. Stop for separate approval before any live workbook write.

## 14. Acceptance tests

### 14.1 Safety

- A `dry_run_evidence` approval is rejected for `--write` before mutation.
- Creation of `deployment_ready_write` approval is refused until an eligible `pass-c-3` dry-run report exists.
- `pass-c-1`, `pass-c-2`, and old approval schemas are permanently refused for live write.
- A stale eligible-report SHA is refused.
- `write=True` with schema validation disabled is refused at the service layer.
- Unknown/new warning kinds or warning-set drift invalidate write approval.
- Only context-validated `scaffold:` warnings are initially confirmable; `dorder:` and `refdel:` remain blockers.
- Blank option `selectable` or `active` may be captured by a pre-`pass-c-3` diagnostic dry-run, but blocks `pass-c-3` plan approval, write eligibility, and `write-approval.json`.
- A matched ZR1/ZR1X RPO retains its existing option ID and dependent OVS identity.
- An ambiguous duplicate becomes an exception and receives no guessed ID.
- A referenced delete cannot be confirmed away.
- Reference fixtures cover `LZ_Interiors.included_option_id`, `color_overrides.option_id`, `color_overrides.adds_rpo`, `model_interior_scope.requires_option_id`, typed `default_selection_rules` targets/conditions, and option-targeted `asset_map.target_id`.
- Temporary readback checks every prepared operation/field and proves coverage of every raw plan operation.
- Any pre-write generation/readiness failure leaves the live workbook byte-identical.
- One blocked target makes an atomic multi-target plan top-level ineligible.
- Every pre-write refusal leaves the workbook byte-identical; an ineligible write exits nonzero.
- An already-applied run cannot replay.
- A post-write verification failure enters `apply_verification_failed`, preserves backup/report evidence, and requires explicit restore/reconciliation.
- Promotion activates target `model_variants` and discovery finds the model.

### 14.2 Compiler coverage and determinism

- Same source/workbook/resolution fingerprints produce byte-identical semantic artifacts.
- Every raw feature and applicable comparator fact has one disposition.
- Every ready row has evidence and exact live headers.
- Every apply operation maps to a ready manifest row; every manifest action maps to an operation or explicit no-op.
- Applying the desired state to a temporary workbook and replanning produces zero unintended operations.
- No copied D.2 decision becomes target truth without current evidence validation.
- Existing target section identity is retained when compatible; at least two agreeing independent active-model precedents can derive a section, while a lone comparator or conflicting precedents create one finite-choice exception.
- Uniform target Price Schedule rows become base prices; scoped conditional rows emit complete override rows; ambiguous qualifiers cannot disappear or borrow comparator values.
- Variant headers/base-price rows reuse exact target variant IDs or produce complete deterministic new rows; missing target variant facts block compilation.
- Reordering raw sheets/rows does not change duplicate-RPO occurrence identity or workbook IDs.
- Duplicate existing rows without a unique semantic match produce an exception rather than fuzzy selection.

### 14.3 Comparator relationships

- Active Grand Sport/Z06 source roles load; inactive scaffolds are rejected as comparator sources.
- An explicit GSX `B6P includes D3V/SL9` target clause compiles with Grand Sport corroboration.
- `Included with PEF` resolves to `PEF includes CAV`.
- A concrete non-product prose fixture with no relationship semantics or product endpoint creates no rule and receives `resolved_not_a_workbook_fact` in the feature ledger.
- Product-like relationship prose with an unresolved endpoint creates a typed exception rather than being dismissed.
- A comparator-only direct rule creates no ready target row.
- An exact exclusive topology with target peer support creates one prefilled confirmation exception.
- A partial/superset peer set cannot auto-accept.
- An explicit complete target group that differs from partial comparator topology still compiles from target evidence; only ambiguous target membership becomes an exception.
- An unambiguous target rule that differs from the comparator still compiles from target evidence with comparator disposition `not_applicable_target_diff`; ambiguous target evidence plus comparator disagreement creates a conflict exception.
- Comparator price differences remain nonportable context and never block an unambiguous target price.
- Duplicate comparator RPO occurrences retain distinct activity: inactive T0E never merges into active topology, and multiple active occurrences make comparator matching ambiguous.
- Inactive comparator group/exclusive members are excluded exactly as the runtime loader excludes them.
- Comparator option-to-interior/non-option facts receive `context_only_nonportable_entity` and are not silently dropped.
- A target-derived interior relationship, when present, resolves only through target interior identity and never reuses comparator interior IDs.
- No target field is derived solely from comparator prices, defaults, IDs, sections, notes, disabled reasons, or copy; a coincidentally equal value must still point to target evidence or a typed resolution.
- A target `replaces` clause without an active workbook phrase-map representation becomes a typed exception; comparator `excludes + replace` topology does not silently decide it.
- Changing the comparator/phrase-map fingerprint invalidates affected evidence and resolutions.
- Swapping comparators does not change an unambiguous target-derived canonical row.

### 14.4 Exception UX

- A resumed run restores exact compile/exception state.
- Each card shows raw evidence, target workbook state, comparator context, gate impact, and row preview.
- Only type-valid actions/payloads are accepted.
- Resolving an exception invalidates the old plan and recompiles affected rows.
- Stale subject evidence reopens the exception.
- No rule/default/price/presentation “copy to all models” action exists.

### 14.5 Live-data proof

- GSX greenfield compiles through existing generation with expected variants and nonzero customer-selectable choices.
- ZR1 reprocess preserves stable identities, closes dependent references, and generates cleanly.
- ZR1X passes through the same reprocess code with no model-specific branch.
- Generated direct rules, rule groups, exclusive groups, defaults, and price rules match manifest semantic signatures.
- Generated validation errors are zero.
- `form-app/data.js` and dealer behavior remain untouched until separately approved promotion/publication.

## 15. Constraints and non-goals

Constraints:

- No unrelated refactor.
- No new dependencies without approval.
- Workbook owns product/business data and reusable phrase/runtime metadata.
- Generated artifacts are never hand-edited.
- Raw imports are never modified.
- No model-specific Python/JavaScript product exceptions.
- Dealer endpoint, payload, Turnstile/security, and submission UX are preserved.
- Existing D.2 evidence remains immutable.
- All transient artifacts remain run-scoped under ignored `form-output/ingest-wizard/**`.

Non-goals for this design implementation:

- live workbook write;
- runtime publication or model promotion;
- dealer-submission changes or live submission testing;
- visual/media pipeline redesign;
- automatic invention of missing colors/interiors/assets;
- retirement of legacy Pass 0–5 libraries or workbook-editor debug routes;
- refreshing existing Stingray/Grand Sport/Z06 product data;
- broad runtime or generator refactoring.

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Comparator behavior is mistaken for target truth | Evidence ladder, exact RPO signatures, no comparator-only ready rows, negative guards |
| Relationship direction is reversed | Workbook-owned phrase direction, target syntax tests, comparator corroboration only |
| Reprocess breaks referenced identities | Desired-state matching, stable IDs, full incoming-reference graph, unconfirmable `refdel` blockers |
| A mechanically valid plan is not deployment-ready | Separate compile/plan/write/deployment readiness and pre-write generator proof |
| User queue remains too large | Compiler owns deterministic rows; comparator creates one group-level proposal; context-only facts stay out of routine queue |
| Broad bulk actions repeat cross-model leakage | No cross-model rule/price/default/presentation copying; typed per-subject resolutions |
| Existing decisions contain useful work | Optional validated migration into proposed exceptions, never silent authority |
| Compiler becomes hidden business logic | All derivations point to raw evidence, workbook metadata, comparator evidence, or typed user resolution; no model-specific exceptions |

## 17. Companion-file impact

- Canonical workbook: inspected/read-only during implementation until a separate live-write approval; no hand edits.
- Generated runtime artifacts and `form-app/data.js`: inspected through scratch generation only; tracked publication unchanged.
- Generator/model config: existing contracts remain authoritative; changes should be limited to generic discovery/promotion parity if tests require it.
- Runtime and dealer flow: inspected-no-change; customer/dealer verification occurs only after a later promotion approval.
- Workbook editor legacy Ingest Review: preserved as debug/compatibility; no production expansion.
- README/docs: update command/status ownership only when corresponding implementation lands; avoid duplicating detailed design outside this file.

## 18. Review gate

Sean approved this production design and authorized implementation beginning with the independently reviewable Milestone 0 safety closure.

Milestones 0, 1, 2, and 2.1 are complete and independently verified. The current canonical manifest is not ready; Milestone 3 remains unapproved and no live workbook write, generation, publication, promotion, deployment, or dealer authority exists.

## 19. Milestone 0 implementation closure — 2026-07-09

Milestone 0 closed the current writer before compiler work. The implemented surfaces are the canonical operation/reference/warning/readback path in `scripts/corvette_form_generator/editor_ops.py`; scoped approvals, pre-write authority, and diagnostic eligibility in `scripts/corvette_form_generator/ingest/wizard/session.py`; diagnostic-only CLI/server/browser exposure; model-variant promotion/discovery parity in `scripts/promote_model.py`; and their focused regression suites. `README.md` now includes the promotion test in the Python metadata gate. No dependencies were added.

Fresh real-data proof:

- Historical D.2 run `20260709-003524-650cae` remained immutable (`0a44e44df4cdb5b057fbe2c891863b63369fb4d6b844a9a96391693a62e52b14` tree digest before and after).
- Fresh ignored run `20260709-184223-960eb1` cloned only D.2 source/profile/selection/decision artifacts, reset to `decisions_complete`, rebuilt the current `pass-c-2` plan, and received only `plan-approval-2` with `scope=dry_run_evidence`.
- The default CLI dry-run emitted `pass-d-2`, `ok=true`, `status=validated_write_blocked`, and `writeEligibility.eligible=false`. It enumerated the permanently diagnostic plan schema, blank option semantics, option-ID churn, referenced deletes, unconfirmable scaffold warnings, and missing price-rule/rule-group product coverage.
- Exact temporary-workbook proof covered all 5,771 raw operations and checked all 5,771 prepared effects. `verification.ok=true`, with no readback errors.
- `stingray_master.xlsx` remained byte-identical and retained the same mtime (`03e8c9671185f238dde7f4bc8e7003da0f74d842d9cc2f76126f938cbb7b54d6`). The run created no `write-approval.json`, `apply-report.json`, workbook edit log, backup, registry publication, runtime publication, or promotion.
- `form-app/data.js` remained `dd60534734c1330085ea74602515e1ab75aa964d3134c230abe0f26217b79e78`; the tracked generated-artifact tree returned to and finished at `fcafc9f18f4dfc7740eec392319510d487cedb413beca093ef031d185a85c124`. README Node tests temporarily regenerated tracked artifacts as an expected test side effect; those test-created files were restored exactly to `HEAD` and were not committed.

Validation:

- Focused Milestone 0 pytest gate: 221 passed plus 7 subtests in 145.37 seconds.
- Full Python suite: 492 passed, 6 failed, plus 7 subtests in 272.35 seconds. The six failures reproduce together from the clean task base in 1.83 seconds and are unrelated baseline drift: the present `asset_map-Sync/` legacy directory, three real-workbook lint/compare expectations, one stale Fable last-session fixture expectation, and one Stingray `display_behavior` characterization expectation. This checkpoint did not rewrite those unrelated tests or data.
- Wizard JavaScript syntax check plus every README Node test surface: 267 passed in 65.31 seconds.
- Workbook package validation: valid, zero issues. Workbook schema validation: valid, zero errors and zero warnings.

Residual risks are the blockers the safety report intentionally detects rather than repairs: current broad-plan blank flags, identity churn, references, and product coverage. Milestone 1 must replace that plan construction with a deterministic headless compiler and comparator evidence index; it must keep the live workbook and tracked publication surfaces untouched.
