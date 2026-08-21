# Workbook Manager Product and UX Recovery Specification

Status: active product recovery; Checkpoint 1 implementation authorized and
started 2026-08-21. Later checkpoints remain gated by §19 and must not begin
automatically.

Recommended implementation reasoning: medium. Escalate only for a specific
workbook-schema, customer-facing copy, data-integrity, or apply/recovery
judgment.

## 1. Decision and authority

The current Workbook Manager is not an acceptable primary user interface for
managing the Corvette form. It successfully implements substantial workbook
safety, relational projection, durable draft, validation, recovery, asset
reconciliation, generation, and publication infrastructure, but exposes that
infrastructure as a database- and workbook-oriented console. The product goal
is different: help an operator understand and manage the form through the
concepts they work with—models, sections, options, groups, availability, rules,
pricing, copy, and assets—without requiring them to mentally reconstruct the
workbook schema.

This specification owns the Workbook Manager's product model, information
architecture, visual language, user-facing terminology, option/group
relationship experience, and first-run/recovery experience. It supersedes
prior claims that the existing Manager UI is product-complete. It does not
reopen or weaken the completed reliability implementation in
`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`.
That specification remains authoritative for projection safety, durable drafts,
ChangeSet identity, preview/approval/apply, rollback, regeneration,
publication, recovery, and single-process serving.

Standing source-of-truth, workbook-safety, approval, validation, and handoff
requirements in `AGENTS.md` apply.

## 2. User goal

The Manager must bridge the gap between workbook rows and the actual form. A
user must be able to answer and act on questions such as:

- What does this option say and where does it appear?
- For which model variants is it standard, available, or unavailable?
- Which exclusive groups and rule groups contain it?
- What other options are in those groups?
- What does selecting it include, require, exclude, replace, or price?
- What pricing rules, variant overrides, default rules, and assets affect it?
- What group heading and selection instruction will a customer see?
- What will change in the workbook and generated form if I save this edit?

The user must not have to browse separate workbook-shaped tables and manually
join IDs to answer those questions.

## 3. Current diagnosis and evidence

The recovery is required because the current UI has concrete functional and
product-level defects:

1. Clicking the first visible option Edit action at a 1440 x 1000 viewport
   renders the editor 4,157 pixels below the viewport, after the 100-row table.
   The page does not scroll, move focus, open a modal/drawer, or announce where
   the editor appeared. A working action therefore looks broken.
2. The Form Structure endpoint groups step sections from only the
   model-specific `section_presentation` subset. The imported `section_master`
   data and generated runtime contract contain the missing relationships, but
   most runtime steps display `no sections mapped`.
3. The database contains connected option, OVS, group, rule, pricing, override,
   asset, and section data, but the active browser has no option-centered or
   group-centered relationship view. Dependency inspection is exposed only as
   part of deletion.
4. Group lists lead with canonical values such as
   `grand_sport_x_excl_1623e1da9d59` even when the same row's notes and member
   options clearly describe an engine-cover choice group.
5. The current display-ID helper merely humanizes unrecognized group IDs and
   the table continues to render the raw canonical value. It does not create a
   useful group name.
6. The customer runtime hardcodes `Related options`, `Choose one`, and
   `Choose one of these related options`; the workbook has no dedicated group
   display-label contract.
7. Edit and delete affordances are repeated across dense row lists. Read-only
   areas still inherit action-oriented table treatment, so the user cannot
   reliably distinguish editable content, reference-only content, disabled
   content, and temporarily blocked content.
8. First-run and stale-projection conditions surface backend lifecycle concepts
   and expected HTTP 404/409 responses instead of a controlled loading or
   recovery state. During the observed first run, projection promotion finished
   immediately before a Manager State backup triggered another status refresh,
   making an unrelated backup action appear to repair the application.
9. `Re-Import Workbook`, `Backup Manager State`, and `Refresh` are presented as
   nearby peer actions without explaining their different targets or effects.
   The existing Refresh handler performs no named operation beyond requesting
   another status read through shared callback behavior.
10. Existing automated browser containment checks prove safety strings and
    route usage but do not prove editor visibility, focus, understandable
    labels, correct read-only affordances, relationship navigation, first-run
    comprehension, or absence of expected-error console noise.
11. The record schema currently defaults every writable column without explicit
    Boolean, enum, or reference metadata to `free_text`. For example,
    `section_presentation_meta` declares `active` as Boolean and `section_id` as
    a reference, but does not classify `display_behavior`, `step_key`,
    `standard_equipment_bucket`, `standard_equipment_group_type`, or
    `auto_added_bucket`. The form therefore accepts arbitrary text for fields
    whose generator/runtime meanings are constrained.
12. Every raw-table row carries an unlabeled comparison checkbox. Selecting two
    rows opens a field-by-field comparison below the table, outside the user's
    immediate context. This arbitrary two-record diff has no demonstrated role
    in editing, validation, or workbook safety and is easily confused with the
    separate disposable workbook review export.

The current verified projection has zero import issues and the workbook is
current. These UX failures are not evidence that the canonical workbook is
corrupt; they are evidence that the Manager presents correct underlying data
through the wrong product model.

## 4. Pinned product principles

### 4.1 Form concepts first

The primary hierarchy is:

```text
model
  -> form step
    -> section
      -> option
        -> availability, groups, rules, pricing, overrides, assets
```

Workbook sheets, SQL tables, source rows, physical keys, fingerprints, and
ChangeSet identities are traceability evidence. They are never the primary
navigation or primary label.

### 4.2 Options and groups are first-class workspaces

An option is not just one `options` row. It is the connected view of every
workbook-authored record that affects that option for the selected model.

A group is not just a group header row or a separate member table. It is a
human-named collection with behavior, members, ordering, related source/target
rules, section context, and a customer-visible presentation contract where
applicable.

### 4.3 Human labels lead; canonical IDs remain intact

Canonical IDs must not be renamed as part of this recovery. The UI leads with
workbook-authored display labels, option RPOs, and option names. Canonical IDs
appear only in an expandable Technical details area, copy control, audit view,
or advanced table browser.

Hash-like IDs must never be converted into fake display names by replacing
underscores or changing capitalization.

### 4.4 Safety states must be understandable

The UI must translate projection, draft, workbook, generated-artifact, and
publication state into plain-language readiness and exact next actions. Raw
state values remain available under System details.

### 4.5 Action and response stay together

Clicking Edit, Add, Delete, Validate, Approve, or Apply must cause an immediate,
visible, focused response adjacent to the user's context. Controls must not
activate content off screen without moving focus and announcing the result.

### 4.6 Visual styling communicates capability

Color alone is insufficient. Editable, read-only, blocked, destructive,
provisional, and applied states require distinct combinations of placement,
text, iconography, borders/backgrounds, and enabled controls.

## 5. Target information architecture

### 5.1 Primary navigation

The normal operator navigation is:

1. **Form Overview** — model readiness, actual form sequence, section coverage,
   draft summary, and clear next action.
2. **Options & Relationships** — searchable option explorer and connected
   option detail.
3. **Groups** — human-named exclusive groups and rule groups with connected
   member management.
4. **Sections & Layout** — actual runtime step/section hierarchy, customer
   labels, ordering, visibility, and section membership.
5. **Images** — the existing asset reconciliation capability in user-facing
   language.
6. **Review & Apply** — human-readable draft summary, validation, approval, and
   guarded write/rebuild flow.

`History`, raw collection tables, projection tools, immutable artifacts,
fingerprints, source coordinates, comparison export, and durable-state backup
move under **Advanced & Recovery**. They remain available but do not compete
with normal form-management tasks.

The existing arbitrary two-row record comparison is not an advanced safety
tool and does not move with the raw table browser. It is removed under §11.

### 5.2 Persistent context

The selected model is one persistent application-level control. Changing it
updates every primary workspace consistently. The header shows:

- selected model;
- plain-language readiness: `Ready to edit`, `Loading latest workbook data`,
  `Workbook changed—reload required`, `Draft awaiting review`, or `Recovery
  required`;
- current draft change count;
- a single context-appropriate primary action.

Internal five-surface state chips move under an expandable System details
panel.

## 6. Option Explorer contract

### 6.1 Search and selection

The operator can search within a selected model by:

- RPO;
- option name;
- canonical option ID;
- section name;
- human group label;
- descriptive text.

Results lead with `RPO — Option Name`, section, availability summary, and small
relationship counts. Selecting a result opens a stable detail workspace; it
does not navigate to a workbook table.

### 6.2 Connected option detail

The option detail must show these coordinated panels:

- **Overview:** RPO, name, customer copy, section/step, base price, selectable,
  display behavior, active state, and form preview where practical.
- **Availability:** a model-variant matrix for standard/available/unavailable,
  plus variant overrides and clear inherited versus overridden values.
- **Groups:** every exclusive group and rule group the option belongs to, using
  human group labels, behavior summaries, member counts, and links to the group
  workspace.
- **Rules:** incoming and outgoing includes/requires/excludes/replaces behavior
  translated into plain sentences while retaining exact technical values under
  details.
- **Pricing:** base price and every applicable conditional price rule, with
  scope and target names.
- **Defaults and overrides:** default selection rules and variant-specific
  behavior.
- **Images:** exact/shared asset coverage and presentation settings using the
  existing reconciliation owner.
- **Technical details:** option ID, physical workbook ownership, source
  sheet/row, model context, and related canonical IDs.

One connected backend read model must supply this view. React must not join or
recompute workbook business rules independently.

### 6.3 Contextual editing

Edit opens a right-side drawer on desktop and a full-screen sheet on narrow
viewports. It must:

- open within the current viewport;
- move keyboard focus to a meaningful heading or first field;
- group fields by user intent rather than workbook column order;
- use human labels with optional technical names underneath;
- keep Save and Cancel visible;
- describe the draft effect before Save;
- return focus to the initiating control after close;
- show the saved change immediately in a persistent draft tray.

### 6.4 Connected navigation and discovery

Every normal entry point must resolve a workbook entity to the same stable
connected workspace. Opening an option from Form Overview, a section, search
results, a group member list, a rule relationship, or Images must open the same
model-scoped Option Explorer detail rather than a separate table-specific copy.
Opening a group from an option or search result must likewise open the same
Group workspace. Back navigation preserves the originating model, workspace,
entity, and expanded context so relationship exploration does not become a new
scavenger hunt.

The normal operator shell must provide one model-scoped cross-entity search.
Results are typed and visually distinguishable as Option, Group, Section, or
Rule results while leading with human labels and RPOs. Exact RPO, approved human
label, and canonical-ID matches rank ahead of descriptive-text matches.
Selecting a result opens that entity's connected workspace; search must not
create a second read model or send users to raw collection tables.

The Manager must also expose named, read-only relationship queries and
diagnostic filters for recurring questions that the projection can answer
deterministically. The initial contract includes:

- options without required image coverage;
- options belonging to more than one exclusive group;
- where an option or group is used in the selected model;
- every incoming and outgoing conflict, requirement, inclusion, or replacement
  affecting an option;
- options whose availability differs across the selected model's variants.

These are connected projection queries, not AI-authored business judgments.
Each result links to the same canonical option, group, section, or rule detail,
states its model scope and filter definition, and remains read-only until an
operator deliberately opens an authorized contextual editor.

## 7. Group Manager and workbook-owned labels

### 7.1 Human group label contract

Add a workbook-owned `display_label` contract for `exclusive_groups` and
`rule_groups`. This is a deliberate workbook-schema and generated-contract
change and requires its own implementation approval and migration review.

The contract is:

- `group_id` remains the immutable canonical identity;
- `display_label` is the concise human name shown in the Manager;
- active exclusive groups rendered in the customer form require a nonblank
  customer-appropriate `display_label`;
- `notes` remains explanatory/internal prose and must not be parsed or silently
  promoted into customer copy;
- generation must validate missing/duplicate/invalid display labels before the
  customer runtime consumes them;
- no automatic label may be inferred from a hash-like ID;
- existing group labels must be proposed in a review artifact and explicitly
  approved before workbook application.

Examples are illustrative, not approved workbook copy:

- `Engine cover choices`
- `Performance brake options`
- `Exterior accent choices`
- `Wheel center cap choices`

### 7.2 Customer runtime presentation

For a visible exclusive group, the customer form uses the workbook-authored
group label as the heading instead of the generic `Related Options` heading.
Selection semantics remain a separate instruction:

```text
Engine cover choices
Choose one
```

or:

```text
Performance brake options
Selection required
```

The runtime must not conflate the group name with the selection requirement.
The generic `Related Options` heading may remain only as a temporary migration
fallback before all promoted visible groups have approved labels; it must not
remain in the completed contract.

### 7.3 Group selection and exploration

The Groups workspace lists and searches groups by human label. Each result
shows group type, selected model, section context where derivable, behavior,
active state, and member count. The canonical ID is hidden under Technical
details.

Selecting a group shows:

- human label and selection/rule behavior;
- explanatory notes;
- all members as `RPO — Option Name` cards or rows;
- member order and active state;
- where the group appears in the form;
- options that reference or are affected by the group;
- customer-form heading/instruction preview for exclusive groups;
- draft changes affecting the group or its members;
- technical workbook lineage under details.

### 7.4 Group editing

Within the existing durable draft lifecycle, an authorized editable group may:

- edit its display label;
- edit supported behavior values through finite controls;
- edit notes;
- add an existing option as a member;
- remove a member after dependency/final-graph checks;
- reorder members;
- activate or deactivate the group or member where the workbook contract allows;
- open any member's connected option detail without losing group context.

Adding a group requires a deliberate canonical ID strategy and all required
fields; the UI must not encourage operators to type hash-like IDs manually.
The implementation specification for group creation must establish whether the
existing generator/authoring convention can safely allocate IDs or whether a
separate approved identifier service is required.

## 8. Sections and form structure

The Form Overview and Sections & Layout views must use a connected,
model-specific form graph that agrees with fresh generated runtime metadata.
They must not join only the `section_presentation` subset.

The view distinguishes:

- navigable runtime steps;
- ordinary option sections;
- context sections;
- standard-equipment buckets, which are not navigable steps;
- summary-only mappings;
- active, inactive, hidden, conditional, and unmapped records.

`No sections mapped` may appear only when the complete connected graph proves
that condition. Standard-equipment buckets must be presented as buckets, not as
broken or missing runtime steps.

## 9. Editable versus read-only visual contract

### 9.1 Editable content

Editable content must have an explicit visible affordance such as `Edit option`,
`Edit group`, or `Edit section`. A whole card or row may be selectable for
inspection, but editing requires a named action. Pencil/trash icons may
supplement text only when the action remains unambiguous.

### 9.2 Read-only content

Read-only content must:

- show a lock/reference icon and a plain label such as `Reference only`;
- state why it is read-only and where its authority lives when useful;
- omit Edit, Delete, Add, and empty Actions columns entirely;
- use a visually quieter but still legible surface;
- remain selectable only when selection opens inspection or navigation;
- never render disabled edit/delete icons, because disabled destructive
  affordances imply that editing may become available through an undisclosed
  action.

### 9.3 Temporarily blocked content

Content that is normally editable but blocked by stale workbook state, a locked
draft, or recovery state is not styled as read-only. It shows `Editing blocked`
plus the exact reason and recovery action.

### 9.4 Destructive actions

Delete/deactivate actions are not repeated as unlabeled icons on every dense
row. They live inside the selected entity's editor or overflow menu, use the
entity name in confirmation copy, show dependent effects before confirmation,
and remain visually distinct from ordinary Save actions.

## 10. Schema-driven editing controls

### 10.1 Complete field classification

Every column in the registry-owned `WRITABLE_COLUMNS` contract must declare an
explicit editing classification. Absence of metadata must not mean free text.
This requirement covers every editable family, including options,
availability, rules, rule/exclusive groups and members, pricing, overrides,
interiors, models/variants, sources/promotion, interior scope/defaults/assets,
runtime steps, section presentation, context sections, and summary mappings.

The registry/schema layer—not React—owns the classification and allowed value
source. Each writable field must be intentionally classified as one of:

- Boolean, including whether blank is permitted as a distinct inherited or
  unspecified state;
- finite vocabulary;
- ordinary, union, or discriminator-dependent reference;
- integer, money, display order, priority, or another constrained numeric
  value with applicable range/format rules;
- URL or another validated structured string;
- intentional short text;
- intentional long-form copy or notes;
- immutable/generated/read-only despite appearing in a record schema.

Free text is allowed for actual copy, labels, notes, and other open-ended
content, but must be declared explicitly. A new writable field with no control
classification is a schema/test failure and must not silently render as a text
box.

Allowed values and references derive from the workbook-domain registry and the
same authoritative enums, registered records, or generated-contract semantics
used by validation. The frontend must not maintain a second list. This recovery
must not invent new business values: where the accepted vocabulary is not
already explicit, implementation must trace workbook rows, generator parsing,
runtime consumers, and validators, then add the proven domain to the registry.
An unresolved product choice follows the approval gate in §19.

### 10.2 Required controls

- Boolean fields use a checkbox, switch, segmented control, or clearly labeled
  finite selector. Optional three-state values visibly distinguish `Yes`, `No`,
  and `Not specified/inherit`; internal `True`, `False`, and SQL-null wording is
  confined to Technical details.
- Small finite vocabularies use radio/segmented controls or a dropdown. Longer
  finite vocabularies use a searchable combobox. The user cannot submit a value
  outside the registered vocabulary.
- References use searchable selectors whose choices lead with human labels and
  show canonical IDs secondarily. Model-scoped selectors show only valid
  records for the active model unless the contract explicitly permits a shared
  target.
- Conditional references update when their discriminator changes. An obsolete
  dependent value is cleared only with an explicit explanation or is marked for
  correction before Save; it is never silently retained as valid.
- Numeric, money, order, priority, and structured-string fields use appropriate
  inputs, constraints, examples, and inline validation instead of accepting
  arbitrary strings until draft review.
- Long-form copy uses an appropriately sized text area with any existing length
  or format guidance. Intentional identifiers remain locked during edit and use
  an approved creation strategy during Add.

An existing workbook value outside the proven allowed set must appear as
`Current value is not valid for this field`, with its exact value available in
Technical details. It must not be silently appended to a dropdown as if it were
an approved choice. Saving requires an explicit valid replacement unless an
approved migration or compatibility contract says otherwise.

### 10.3 Section Presentation example

The Section Presentation editor is the minimum acceptance example, not the
limit of this requirement:

| Field | Required control behavior |
|---|---|
| `section_id` | Searchable reference selector using the section's human label, with canonical ID secondary. |
| `step_key` | Searchable selector restricted to the proven step/bucket targets allowed for the selected model. |
| `display_behavior` | Optional finite selector sourced from the registered display-behavior domain accepted by generation/runtime. |
| `standard_equipment_bucket` | Explicit optional Boolean/three-state control; never a text field. |
| `standard_equipment_group_type` | Optional finite selector sourced from the proven group-type domain. The currently observed `trim_equipment` value does not by itself establish the complete domain. |
| `auto_added_bucket` | Explicit optional Boolean/three-state control; never a text field. |
| `section_display_order` | Constrained integer/order input with inline format validation. |
| `active` | Explicit Boolean control. |
| `display_label` and `notes` | Deliberately classified open text, using short-text and long-text controls respectively. |

The same audit and classification is required for every other writable field;
passing this example alone is insufficient.

### 10.4 Validation timing and completeness proof

Control-level validation occurs on selection/change or blur and again before
Save. Errors name the field, explain the accepted choice or format in user
language, and appear beside the field. Backend and final-graph validation remain
authoritative, but routine typos in closed-vocabulary/reference/typed fields
must not survive until Draft Review.

The implementation must generate or test a complete editable-field control
matrix directly from `WRITABLE_COLUMNS`. The gate fails when:

- any writable field lacks an explicit classification;
- a Boolean, enum, reference, typed number, or structured value renders as
  unrestricted text;
- a frontend allowed-value list disagrees with registry authority;
- a reference selector offers an invalid scope or target family;
- optional/required/blank semantics disagree between the control and backend;
- adding a writable column would fall back to free text without a deliberate
  registry decision.

## 11. Selection and comparison contract

The unlabeled comparison checkbox column and the below-table `Record
Comparison` panel are removed. Arbitrarily comparing two workbook-shaped rows
does not support the option-, group-, or section-centered workflows and is not
part of workbook protection, validation, draft review, or apply/recovery.

No primary or advanced table may show a selection checkbox without an
immediate, named purpose. If a future approved workflow genuinely needs row or
member selection, the interface must state the action next to the selector,
show a persistent selection summary/action bar, limit eligible records, and
clear selection when the context changes. Selection must never be introduced
merely because a table can support it.

`Export Workbook Review Copy` is separate. It remains under Advanced &
Recovery as a workbook-level, non-authoritative diagnostic with clear output
and safety copy. It must not use or visually resemble the removed row-comparison
checkboxes.

## 12. Action naming and operational clarity

Every operational action must name its target and outcome. The completed UI
uses this terminology unless implementation evidence requires a clearer exact
variant:

| Current label | Required user-facing label | Exact meaning |
|---|---|---|
| `Re-Import Workbook` | `Reload Latest Workbook Data` | Read `stingray_master.xlsx`, verify it, and replace the disposable browsing projection. Does not change the workbook. |
| `Backup Manager State` | `Back Up Drafts & History` | Copy the durable Manager database containing drafts/recovery/audit state. Does not back up or change the workbook. |
| `Refresh` | Remove, or `Refresh Screen Status` only where a manual status reread is proven necessary | Reread status only. It must never imply workbook import, backup, validation, or regeneration. |
| `Refresh inventory` | `Refresh WordPress Image Inventory` | Re-fetch image inventory and rebuild reconciliation status. Does not upload, delete, or change media. |
| `Export Disposable Comparison` | `Export Workbook Review Copy` | Create a non-authoritative comparison workbook that cannot replace the canonical workbook. |
| `Freeze ChangeSet` | `Lock Draft for Validation` | Stop ordinary editing and bind the current draft operations into one exact ChangeSet. |
| `Preview ChangeSet` | `Validate Draft Against Workbook` | Run the exact locked draft through final-graph workbook validation without writing. |
| `Approve Exact Preview` | `Approve Validated Changes` | Approve only the exact successful validation result. Does not write the workbook. |
| `Apply and Rebuild` | `Write Approved Changes & Rebuild Form Data` | Back up, write the approved workbook changes, validate/read back, regenerate affected local model data, and publish the local registry. Does not deploy or submit to a dealer. |
| `Cancel Draft` | `Cancel Draft and Keep Audit Record` | End the draft without deleting its immutable history. |

These distinctions must be visible next to the control, not available only in
an external guide or tooltip. Advanced & Recovery groups actions by target:

- Workbook data
- Drafts and history
- Image inventory
- Review exports
- System status

No screen presents unrelated actions as visually equivalent peers.

## 13. First-run, freshness, error, and recovery experience

### 13.1 First-run state machine

Before normal workspaces render, the application resolves one of these states:

- `Starting Workbook Manager`
- `Loading and checking workbook data`
- `Ready to edit`
- `Workbook changed—reload latest data`
- `Draft requires attention`
- `Workbook recovery required`
- `Cannot reach Manager backend`

Each non-ready state has one primary next action, an explanation of what is and
is not safe, progress where measurable, and expandable technical detail.

The UI must not render stale/empty tables as if they were current while a
long-running import is active.

### 13.2 Expected HTTP states

The client must not make requests that are already known to violate the current
state. A new draft that has not persisted is represented locally and does not
produce a user-visible 404. A stale projection blocks asset/editor requests in
the client and offers Reload Latest Workbook Data instead of generating a set of
409 responses.

When the server still returns an error, the interface shows:

- what action failed;
- what target was unaffected;
- whether the workbook changed;
- the exact safe next action;
- technical status/code/detail under expansion.

Expected lifecycle handling must not fill the browser console with unexplained
errors during a successful first-run or recovery flow.

### 13.3 Completion feedback

Every import, backup, inventory refresh, validation, approval, and apply action
has a persistent result tied to the initiating control. A success notice cannot
disappear merely because another status request finished. An unrelated action
must never appear to clear or repair a warning without explaining the state
transition that actually occurred.

## 14. Review and Apply experience

Review & Apply leads with human statements such as:

- `BC4 — Blue LS6 Engine Cover: availability changed for Coupe 2LT`
- `Engine cover choices: BCP moved from position 3 to position 2`
- `Exterior accent choices: customer group label changed`

Workbook sheet/row, physical key, ChangeSet ID, fingerprints, immutable attempt
payloads, and separate output-state evidence remain available in expandable
technical sections.

The review flow remains:

```text
edit draft
  -> lock draft for validation
  -> validate against workbook
  -> approve validated changes
  -> write approved changes and rebuild form data
```

The UI must describe Save as saving draft intent. It must never imply that Save
changed the workbook or regenerated a model.

## 15. Source-of-truth and preserved boundaries

- `stingray_master.xlsx` remains canonical for business data, group labels,
  group membership, rules, copy, pricing, availability, and asset metadata.
- SQLite remains a disposable verified projection plus durable Manager-owned
  workflow/recovery state; it does not become product authority.
- Connected read models may join projected data for presentation but may not
  invent business outcomes or write around the existing durable operation path.
- All edits continue through durable draft operations, exact ChangeSet,
  validation, approval, guarded apply, rollback, regeneration, and publication.
- No direct workbook write, generated-artifact edit, or hidden React business
  rule is introduced.
- WordPress media upload/delete/rename, deployment/cache purge, and dealer
  submission remain outside Manager scope.
- Dealer endpoint, payload, Turnstile/security behavior, and submission UX remain
  untouched.

## 16. Phased implementation

Each checkpoint is independently reviewable. Do not begin the next checkpoint
automatically.

### Checkpoint 1 — readiness shell and read-only connected explorer

- Replace the default landing experience with the first-run/readiness state
  machine.
- Add the model-scoped read-only Option Explorer and read-only Group Explorer.
- Add backend connected read models for option and group details.
- Add model-scoped cross-entity search across options, groups, sections, and
  rules, with every result resolving to the same connected entity workspace.
- Add the initial named relationship diagnostics from §6.4 as read-only
  projection queries with explicit model scope and definitions.
- Move current raw table navigation and maintenance controls under Advanced &
  Recovery without deleting them.
- Remove the unlabeled row-comparison checkboxes and arbitrary two-record diff;
  preserve the separately named disposable workbook review export.
- Make canonical IDs and lineage secondary.
- Do not change workbook schema, create draft operations, or change customer
  runtime output.

Exit gate: a copied-workbook browser session can search for an option, see all
connected group/OVS/rule/pricing/asset relationships, open a group by human
description/status, inspect named members, and recover from stale/first-run
state with no unexplained console errors. Cross-entity search distinguishes and
opens option, group, section, and rule results; opening the same entity from
search or a relationship returns the same stable detail workspace; and the
initial named diagnostics return traceable, model-scoped results. Workbook,
generated, and publication bytes remain unchanged.

Checkpoint 1 completed 2026-08-21. The Manager now resolves readiness before
rendering normal workspaces; exposes model-scoped connected option, group,
section, and rule projections; ranks typed cross-entity search results to stable
destinations; and serves the five named diagnostics as bounded read-only
queries. The normal shell leads with Form Overview, Options & Relationships,
Groups, Images, and Review & Apply. Raw collection browsing and history remain
under Advanced & Recovery. Arbitrary two-row comparison was removed, while the
separate workbook review export remains intact. Group labels in this checkpoint
use existing canonical IDs when readable or factual group/section status when
hash-like; notes were not promoted into label authority and no workbook display
label was invented.

Acceptance evidence: focused RED/GREEN API and shell tests passed; the complete
Workbook Manager suite passed 185 tests plus 36 subtests with two intentional
slow-gate skips; the frontend production build passed; a headless Chrome session
proved stale recovery, readiness, model-scoped 5ZU search, connected option to
group navigation, named members, and a 390 x 844 layout with no horizontal
overflow. Protected pre/post SHA-256 manifests matched for
`stingray_master.xlsx`, all tracked `form-output/` artifacts, `form-app/data.js`,
and the customer runtime files. No workbook schema, draft-write lifecycle,
generated contract, customer runtime, dealer, media, deployment, or publication
behavior changed.

PR 37 repair, 2026-08-21: the first GitHub run did not report an assertion
failure; it reached the complete shared-fixture Manager group after all earlier
selected stages passed, then GitHub cancelled the job at the former 15-minute
limit. The required job now allows 25 minutes without changing catalog
selection or adding Layer 4. Review also found that the two entity-specific
named diagnostics were implemented in the API but unreachable in the connected
UI because their landing-page controls were disabled after entity detail had
replaced that page. Connected option detail now exposes `Where this option is
used` and `Show option relationships`; connected group detail exposes `Where
this group is used`, with results kept beside the selected entity. This is a
read-only Manager UX correction only; Checkpoint 2 remains gated and unstarted.
The exact local catalog-selected PR path then passed all ten stages in 793.239
seconds: Layer 0 owners, composed Layer 1 candidate, protected-artifact guard,
Fable validators, lockfile-driven frontend build, and the complete Manager group
(`185 passed, 2 skipped, 36 subtests passed`).

### Checkpoint 2 — group display-label contract and reviewed migration

- Add registry/workbook/schema/projection/generated-contract ownership for
  `display_label` on exclusive and rule groups.
- Produce a complete review artifact for every existing active group and its
  proposed label; do not infer or apply labels silently.
- Obtain explicit user approval for the actual customer-facing label set.
- Apply approved workbook rows through the guarded workbook path and regenerate
  affected artifacts.
- Keep the customer runtime fallback unchanged until all promoted visible
  exclusive groups have approved labels and the all-model gate passes.

Exit gate: every group has an approved human label or an explicit non-rendered
classification; workbook package/schema and fresh generation gates pass; no
partial customer-runtime label migration is published.

### Checkpoint 3 — contextual option and group editing

- Add in-viewport drawer/sheet editing to the connected views.
- Support group label, behavior, notes, membership, order, and active-state
  edits through existing finite/reference schema controls.
- Classify every registry-writable field under §10 and replace every accidental
  free-text fallback with its schema-driven Boolean, finite, reference, typed,
  structured, or deliberately open-text control.
- Show editable/read-only/blocked states using the visual contract in §9.
- Add the persistent human-readable draft tray.

Exit gate: copied-workbook browser tests cover option edit, group edit,
add/remove/reorder member, dependent refusal, full reversion, and draft resume;
the registry-derived control matrix covers every writable field; constrained
values cannot be mistyped or deferred as arbitrary review errors; all actions
remain draft-only.

### Checkpoint 4 — correct form graph and contextual section management

- Replace the incomplete structure join with the full connected form graph.
- Integrate section/step editing through the same drawer and draft tray.
- Distinguish standard-equipment buckets and other non-navigable structures.
- Prove graph parity against fresh generated runtime metadata for every promoted
  model.

Exit gate: the Manager reports no false unmapped sections, and every displayed
step/section relationship has workbook and fresh-runtime evidence.

### Checkpoint 5 — customer group headings and complete terminology migration

- Render approved workbook-owned exclusive-group labels in the customer form.
- Render selection semantics as secondary instructions.
- Remove the generic completed-state `Related Options` heading.
- Replace ambiguous Manager lifecycle/maintenance labels and group actions with
  the terms in §12.
- Add focused responsive/accessibility/browser regression coverage.

Exit gate: all promoted model forms use approved group labels, existing
selection behavior remains unchanged, all affected runtime tests pass, and no
dealer behavior changes.

### Checkpoint 6 — Review & Apply presentation recovery

- Replace table/lineage-first draft descriptions with human entity/change
  summaries.
- Keep exact lifecycle evidence collapsed but reachable.
- Complete desktop and narrow-viewport flows from edit through successful
  guarded Apply and Rebuild against disposable copies.

Exit gate: an operator can explain what will change, what Save did, what
validation proved, and what Apply and Rebuild will touch without reading
technical IDs or the external user guide.

## 17. Validation strategy

### Documentation-only specification checkpoint

- Review the spec against live React, FastAPI, registry, runtime, and test
  evidence.
- Run `git diff --check`.
- Run the Fable loop validator because `fable5loop/STATE.md` changes.

No code/browser test is required merely for authoring this specification.

### Implementation checkpoints

Use focused tests while editing and one broader affected-surface suite at each
checkpoint. Required coverage includes:

- connected option/group API response contracts and query bounds;
- stable entity identity and preserved navigation context across search and
  relationship entry points;
- typed cross-entity search ranking, model scoping, and destination coverage;
- deterministic named-diagnostic definitions, query bounds, and traceable
  results for every §6.4 query;
- exact projection/workbook identity and read-only behavior;
- option/group relationship completeness;
- form-graph parity with freshly generated runtime metadata;
- group-label workbook registry, schema, generation, and runtime contracts;
- drawer visibility, focus, close/return-focus, Save/Cancel proximity, and
  narrow viewport behavior;
- absence of edit/delete controls on read-only surfaces;
- absence of unlabeled or purposeless row-selection checkboxes and the removed
  arbitrary record-comparison panel;
- an exhaustive registry-derived matrix proving every writable field has an
  explicit control classification and no constrained field falls back to free
  text;
- finite-value, Boolean/blank-state, reference-scope, conditional-reference,
  numeric/structured-input, and invalid-legacy-value behavior;
- inline prevention of closed-vocabulary/reference/typed-input errors before
  draft Save while preserving backend/final-graph validation;
- clear blocked-versus-read-only presentation;
- first-run, stale, long-import, backend-unreachable, and recovery states;
- absence of unexplained expected 404/409 console errors;
- human-readable draft summaries bound to exact technical artifacts;
- unchanged selection/rule/pricing behavior when only presentation changes;
- protected workbook/generated/publication hashes for read-only checkpoints;
- workbook package/schema, affected-model generation, registry publication,
  cache-version, rollback, and replay proof for approved write checkpoints;
- safe browser proof with copied workbooks only—no live dealer submission.

Accessibility acceptance includes keyboard reachability, visible focus,
semantic headings/regions, non-color status cues, accessible action names,
dialog/drawer focus trapping where applicable, and no icon-only primary or
destructive actions.

## 18. Non-goals

- Rebuilding the Manager as a generic spreadsheet editor.
- Making SQLite canonical.
- Changing option availability, rules, pricing, group membership, labels, or
  other business data without explicit workbook-authored decisions.
- Automatically generating customer-facing group labels from IDs, notes, or
  member names.
- Removing advanced traceability, recovery evidence, or safe guards merely to
  simplify the visible UI.
- Changing WordPress media, deployment, production cache, dealer submission, or
  customer identity/security behavior.
- Adding a dependency or new design system without separate approval.
- Preserving a generic row-comparison feature solely because it already exists.

## 19. Approval gates and next action

Checkpoint 1 began on 2026-08-21 after the completed fast layered validation
specification and evidence moved to
`docs/archive/completed-specs/fast-layered-validation/`. Its bounded code
surface and acceptance test inventory must be confirmed before implementation
edits. Before Checkpoint 2 writes the workbook or changes a generated contract,
obtain explicit approval for:

- the `display_label` workbook-schema addition;
- the complete proposed group-label list;
- the customer-runtime switch from generic headings to workbook-owned labels.

Checkpoint 3 may encode already-proven accepted vocabularies and references as
registry metadata without creating new business behavior. If repository and
workbook evidence do not establish a field's complete allowed domain, stop for
an explicit product/workbook decision instead of guessing choices or leaving
the field as accidental free text.

Checkpoint 1 is complete. Do not begin Checkpoint 2 automatically. Its active
gate remains explicit approval for the `display_label` schema addition, the
complete reviewed group-label list, and the customer-runtime heading switch.
