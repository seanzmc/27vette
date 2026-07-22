Verdict: hold for another spec revision.

The architecture is substantially better and most of the complexity protects real failure boundaries. However:

- It still invokes a legacy Stingray runtime path.
- The recorded baseline is stale.
- The lifecycle does not correctly encode retry permissions or interrupted applies.
- The import gate is carrying more runtime machinery than necessary.

Findings

1. High — Runtime parity explicitly depends on the legacy Stingray compatibility writer

Proven:

- The spec requires changing and testing write_stingray_compatibility_artifacts() at docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md:262-268.
- That function describes itself as a legacy writer at scripts/corvette_form_generator/production.py:657-665.
- generate_model_artifacts() routes Stingray through that writer at scripts/corvette_form_generator/model_generation.py:71-78 and :182-190.
- The proposed acceptance owner, tests/test_generate_form_model_discovery_cli.py, currently asserts those compatibility JSON/CSV outputs at tests/test_generate_form_model_discovery_cli.py:83-90.

This violates the requested “primary runtime workflow only” boundary.

Recommended correction:

- Remove the production.write_stingray_compatibility_artifacts() change from Section 3.8.
- Remove scripts/corvette_form_generator/production.py from the expected implementation surfaces unless another non-legacy requirement genuinely needs it.
- Do not place the isolation proof in the existing CLI compatibility assertions.
- Have contract_parity.py use the current canonical source assembly/runtime-contract path only:
  - discover the ModelConfig;
  - override the temporary workbook/root;
  - call the canonical source assembly used by the current model generator;
  - write only the resulting canonical form-output/runtime/<slug>-runtime-contract.json;
  - assert that no compatibility, inspection, preview, draft, registry, or tracked output was written.
- Own that proof entirely in tests/test_workbook_manager_generated_parity.py.

The current comparator, scripts/compare-generated-contracts.mjs, is generic and not itself a legacy path.

2. High — “Published” can still resolve through compatibility-capable promotion semantics

Proven:

The spec defines published as merely active plus promoted_to_runtime=True at ...workflow.md:419-431, then uses that set for parity at :580-583.

But load_registry_promotions() still accepts historical forms:

- empty/header-only promotion metadata preserves a legacy fallback: scripts/corvette_form_generator/registry_promotion.py:194-204;
- missing artifact_type defaults to draft_artifact: :214;
- accepted types include current_generation, draft_artifact, and runtime_contract: :231-234;
- legacy_alias is carried by the reader: :243;
- non-runtime-contract artifact resolution remains supported at :263-282.

Recommended correction:

Define the parity set more narrowly than the compatibility-capable promotion reader:

- active promotion row;
- promoted_to_runtime=True;
- artifact_type == "runtime_contract";
- artifact path resolves to the canonical runtime_contract_artifact_path(...);
- model is discoverable by discover_generation_model_configs().

Fail the parity preflight if a promoted row does not satisfy that current contract. Do not generate from current_generation, draft_artifact, compatibility JSON/CSV, or a legacy registry fallback.

The existing legacy_alias field can be preserved as workbook-owned metadata, but this pass should neither consume nor test it.

3. High — The recorded baseline is already stale

Proven by a fresh run:

text
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
2 failed, 26 passed, 2 skipped


Failures:

- TestStagingWorkflow.test_scaffold_model_rejected
- TestComparisonExport.test_export_preserves_unmanaged_and_row_counts

The spec records only one failure at ...workflow.md:56-66.

The second failure is directly relevant to Sections 3.6, 3.7, and Pass 4: the comparison export removes 978 trailing blank PriceRef rows rather than preserving the source sheet exactly.

Recommended correction:

Update the baseline to two failures and assign them explicitly:

- scaffold expectation → Pass 2 model lifecycle matrix;
- comparison-export physical preservation → Pass 4 copy-plus-overlay reconstruction.

Do not let Pass 4 report the second failure as a newly introduced regression.

4. High — Lifecycle states contradict their allowed actions

Proven:

The graph allows:

- every preview_failed to return to changeset_emitted: ...workflow.md:298-300;
- every apply_failed to return to applying: :329-331.

But the outcome table says:

- semantic preview failures must be cancelled and recreated: :375-379;
- invalid/schema/readback apply failures must not be blindly retried: :385-389.

Therefore manager state alone cannot determine the “exact allowed verbs” claimed in Pass 6 and the acceptance matrix.

Recommended correction:

Use outcome-specific states, for example:

- preview_retryable — lock/transient read failure with unchanged identity;
- preview_rejected — invalid, empty, schema, bool, or warning blocker;
- apply_retryable — proven untouched transient pre-save failure;
- apply_rejected — invalid/binding/schema/warning failures;
- retain restored and workbook_state_unknown because they carry distinct physical evidence.

Then make the transition graph and Section 4.1 table agree exactly. Avoid a generic failure state whose allowed verbs depend on hidden status inspection.


5. High — Interrupted applying work has no restart recovery contract

Inferred from an omitted required transition:

The spec persists applying, but only defines outcomes from a normally returning writer call. It does not say what happens if the process exits, is killed, or crashes after durable state becomes applying.

That is precisely when the workbook may be:

- unchanged;
- saved but not receipted;
- restored;
- saved with log failure;
- physically unknown.

Recommended correction:

Pin the crash behavior:

- Persist the approved -> applying transition atomically before invoking the shared writer.
- Store a unique apply-attempt identity and enforce one active attempt per ChangeSet.
- On startup, any orphaned applying record becomes workbook_state_unknown; never retry automatically.
- Require the existing manual-resolution process to prove base hash, exact final rows, or preserve abandoned_unknown.
- A repeated API request must first return an existing terminal receipt or reject an active attempt; it must not invoke the writer again.

Without this, the stated idempotency guarantee at :358-359 is not implementation-ready.

6. Medium — Exception evidence is underspecified

Proven:

preview_changeset() and apply_changeset() can raise exceptions from workbook reads or the shared writer; they do not convert every exception into a returned service dictionary. For example, preview_changeset() calls live fingerprinting and apply_batch() without a broad exception boundary at scripts/corvette_form_generator/workbook_domain/service.py:63-98.

The spec says to persist returned dictionaries unchanged and discusses “transient read exceptions,” but does not define the durable record for an exception that returned no dictionary.

Recommended correction:

Define one manager-owned attempt-envelope schema containing:

- phase;
- attempt ID;
- ChangeSet/preview/approval identities;
- started/completed timestamps;
- returned artifact verbatim, when one exists;
- exception class/message when no artifact exists;
- independently proven workbook state;
- resulting manager state and allowed verbs.

This is manager evidence, not an extension of the public ChangeSet service schemas.

7. Medium — Runtime generation inside every projection promotion is probably unnecessary coupling

Inferred architectural simplification:

Pass 4 runs two full generations per published model during every verified import at ...workflow.md:577-583. That makes browsing-projection availability depend on generator health even though the manager does not publish or run customer runtime output.

It also duplicates four other proofs:

- sheet/column reconciliation;
- managed-row accounting;
- exact source lineage;
- copy-plus-overlay parity.

Recommended direction:


- Make exact managed semantic readback plus workbook package/schema validation the production projection-promotion gate.
- Keep isolated canonical runtime-contract parity as a slow acceptance/regression gate for the importer/reconstruction implementation.
- After an actual workbook write, keep the primary affected-model generation and registry verification outside the manager, as already stated at :674-680.

If runtime parity intentionally remains a production import blocker, document why exact semantic reconstruction is insufficient and ensure it uses only the primary runtime-contract path described in Findings 1–2.

8. Medium — Pass 6 duplicates shared-writer readback

Proven:

Pass 6 requires another exact affected-row readback before terminal applied at ...workflow.md:643-644.

The shared writer already performs live exact-row verification at scripts/corvette_form_generator/editor_ops.py:1423-1458, and the service carries that verification into the receipt at workbook_domain/service.py:203-223.

Recommended correction:

Do not add a second manager readback. Require:

- a formal workbook-change-receipt-1;
- status == "applied";
- workbookState == "saved";
- passing receipt verification;
- exact artifact bindings.

A second independently implemented readback adds another validation path without adding authority.

9. Medium — Full managed-column ownership is not pinned tightly enough

Proven gap:

The spec requires classification of every managed column and distinguishes required, optional, and opaque columns at ...workflow.md:216-247. But the current shared registry explicitly says headers come from the sheet rather than the registry at workbook_domain/registry.py:29-31, and it does not enumerate every writable/free-text column.

“Extend the registry with metadata needed” does not fully tell the implementer:

- which owner provides the complete allowed-column set;
- which fields are required on add versus required only for active rows;
- whether a known optional column absent from a sheet may be added by a ChangeSet;
- whether opaque columns may appear in draft/update payloads;
- how deletes treat requiredness.

Recommended correction:

Pin these rules:

- the registry owns the complete writable field set per family;
- required-on-add and required-on-effective-active-row are explicit and separate if needed;
- opaque columns are preserved but never manager-writable;
- absent optional headers cannot be synthesized by an ordinary row edit;
- delete operations are exempt from after-value requiredness;
- add/update effective final rows are checked after coalescing.

10. Low — Pass 7 contains a small circular enablement statement

At ...workflow.md:666-668, the write action is re-enabled only after “Passes 1–7 gates pass,” while the Pass 7 exit gate needs to prove that only the bound service can write.

Change this to:

- keep the route disabled while implementing Pass 7;
- run all non-write Pass 7 gates;
- enable the route as the final Pass 7 change;
- run the disposable end-to-end write proof;
- only then close Pass 7.

Complexity assessment

Keep these elements; they protect distinct proven risks:

- split projection and durable-state databases;
- candidate-file promotion rather than in-place import;
- reader draining and request-scoped connections;
- SHA-256 plus mtime binding;
- exact immutable ChangeSet/preview/approval/receipt persistence;
- family-specific ownership matrix;
- workbook-preserved sheets and opaque-column treatment;
- post-save restoration ownership in the shared writer;
- explicit unknown physical workbook state.

Simplify these elements:

- remove all legacy compatibility writer work;
- use a strict canonical runtime-contract publication selector;
- move generated parity out of every import unless there is a documented reason it must block projection promotion;
- remove duplicate manager readback;
- split ambiguous failure states rather than attaching hidden per-outcome permissions;
- consolidate repeated parity requirements currently spread across Sections 3.8, Pass 4, Sections 8–9, and the handoff.

Primary runtime workflow the spec should acknowledge

Only:

text
canonical workbook
→ discover_generation_model_configs()
→ canonical model source assembly/runtime-contract generation
→ form-output/runtime/*-runtime-contract.json
→ generate_registry.py for separately authorized publication
→ form-app/data.js
→ static customer runtime


For this manager reliability pass:

- generation is isolated verification or a post-write external gate;
- registry publication remains outside the manager;
- no compatibility JSON/CSV writer;
- no current_generation or draft_artifact promotion input;
- no legacy fallback registry;
- no legacy alias behavior is exercised or changed;
- no ingest deployment-proof/runtime pipeline is involved.

Validation performed

- Reviewed the live spec and relevant registry, generator, service, writer, manager, README, and tests.
- Ran tests/test_workbook_manager.py: 2 failed, 26 passed, 2 skipped.
- Final worktree remained clean.
- No workbook, generated artifact, runtime registry, source file, or spec was modified.

# Addendum from the completed independent review: four material gaps should be added to the prior findings.

1. High — Two-database migration is underspecified

...workflow.md:76-96, 360-364, 500-552

The current WBM_DB contains both projection and journal tables, but the spec does not define the first-start migration into two files:

- schema/version marker;
- atomic and idempotent copy;
- duplicate prevention;
- crash recovery;
- rollback;
- disposition of the original database.

Pass 2 starts changing storage consumers before Pass 3 initializes both databases. Move migration ownership ahead of those changes and pin its transaction/restart behavior.

2. High — restored has conflicting meanings

...workflow.md:119-125, 329-355, 388

restored can mean:

- a retryable failed apply whose backup was restored; or
- a terminal manual resolution of workbook_state_unknown.

Those have different import and retry permissions. Use distinct states such as apply_restored_retryable and manually_resolved_restored, or persist an explicit resolution kind and derive permissions from it.

3. High — Stale-projection permissions are missing

...workflow.md:93-96, 115-125, 601-614

The projection becomes stale after a write, but Pass 5 can still build drafts from projection rows. The spec does not define whether stale projections permit:

- browsing;
- export;
- draft creation;
- preview;
- approval;
- import.

Recommended rule: allow clearly labeled browsing/history only; block new drafts, preview, approval, and write until verified re-import succeeds.

4. Medium — UI work is split prematurely

...workflow.md:516-522, 650-672

Pass 2 changes API metadata and renders finite controls before Passes 3–6 establish the final projection, connection, and lifecycle payloads. That risks rewriting the UI twice.

Keep Pass 2 backend-only: registry/catalog parity, ownership, requiredness, and schema metadata. Move actual control rendering and workflow presentation to Pass 7 unless Pass 2 pins the final API schema.

Also tighten the Pass 6 exit gate at :646-648: replace “failed/restored work remains visible and retryable” with “remains visible with exactly the recovery verb permitted by Section 4.1.” Several failure classes are intentionally not retryable.

These reinforce the same overall verdict: Pass 1 is actionable, but the complete seven-pass specification should remain on hold pending another revision.