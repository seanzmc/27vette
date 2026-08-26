# Workbook Manager Product and UX Recovery Specification

Status: active product recovery. Checkpoint 1 merged through PR 37 at `aa28e8a`.
Checkpoint 2 completed on 2026-08-23 at implementation commit `ff28eb5` and
passed full-inventory Release candidate run 32626231858. Checkpoint 3A/3B's
registry/schema/reference slice completed locally on 2026-08-23; its commit,
`3085d87`, is followed by this closeout. PR and required full-inventory CI
evidence are recorded at delivery. Checkpoint 3C's reusable editor shell
completed locally on 2026-08-24 and was opened as PR 42; its initial delivery
head passed full-inventory Release candidate run 32775301054. The review-follow-up
head reruns that required evidence after push. Checkpoint 3D was implemented
locally on 2026-08-25, received its review fixes on the PR head, and merged
through PR 45 at `3a8369b` on 2026-08-26; its full delivery evidence, including
the post-sync CI rerun and both Codex review-bug fixes, is recorded below.
Checkpoint 3E completed locally on 2026-08-26; its delivery evidence is recorded
with the PR. Checkpoint 3F and Checkpoints 4–6 remain separately gated by §19
and must not begin automatically.

Checkpoint 2 added the approved workbook schema/data and additive generated
label fields, but did **not** authorize or perform the Checkpoint 5 customer
heading switch, a group-ID strategy, a new dependency, deployment, media
mutation, or dealer behavior. A coding agent must re-resolve the live branch,
PR, repository, and workbook state before relying on any recorded baseline.

Recommended implementation reasoning: medium for read-only UI/query work; high
for schema, migration, workbook-write, generated-contract, customer-runtime,
concurrency, or apply/recovery work. Escalate only when new decision authority
is required, not merely because implementation spans multiple files.

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

### 1.1 Authority order and conflict handling

The coding agent resolves instruction authority in this order:

1. `AGENTS.md` for repository conduct, protected boundaries, validation, and
   handoff requirements.
2. `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`
   for projection, durable draft, immutable ChangeSet, preview, approval,
   guarded apply, rollback, regeneration, publication, and recovery behavior.
3. This specification for the relational Manager product model, connected read
   models, editing experience, terminology, and checkpoint requirements.
4. `workbook-manager/README.md` and the root `README.md` for current commands and
   operator instructions.
5. Live code, workbook shape, generated contracts, tests, and workflow output as
   implementation evidence.

A lower source must not silently override a higher source. When the live code
or workbook contradicts this specification, the agent records the discrepancy
and determines whether it is implementation debt, stale specification text, or
an unresolved product decision. The agent may correct stale implementation
facts in this specification during the authorized checkpoint, but may not
invent business behavior to resolve the conflict.

### 1.2 Required checkpoint preflight

Before the first implementation edit, the coding agent must:

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
```

Then it must read or inspect, at minimum:

- `AGENTS.md`;
- this specification;
- the reliable workflow specification named above;
- `workbook-manager/README.md`;
- the fixed `Current handoff` block in `fable5loop/STATE.md`;
- the current implementation files named by the authorized checkpoint;
- the current tests that own those files or behaviors;
- the current PR/check state when work continues an existing pull request.

The agent must identify uncommitted user work before editing and must not stage,
rewrite, or clean unrelated files. If the inspected commit differs from the
baseline above, it must summarize material drift and update the working
definition of done before implementation.

### 1.3 Required working definition of done

Every checkpoint begins with a concise, written definition of done containing:

- authorization received and checkpoint number;
- current diagnosis with source/test evidence;
- exact intended operator outcome;
- source-of-truth owner for every changed value or behavior;
- expected files, workbook families, generated artifacts, and API surfaces;
- protected files and behaviors that must remain byte- or behavior-identical;
- RED tests to add or identify before implementation;
- focused, broader, browser, and CI gates;
- rollback plan for any workbook or generated-output write;
- explicit stop conditions and unresolved decisions.

The definition may be recorded in the checkpoint section, a progress update, or
an authorized run receipt. It must not become a competing third progress file.

### 1.4 Mandatory stop conditions

Stop the current checkpoint and request direction when any of these occurs:

- the requested behavior requires choosing business data, customer copy,
  availability, pricing, defaults, membership, or rule semantics not already
  established by authority;
- a new workbook column, generated contract, public API break, dependency,
  security boundary, deployment path, or group-ID strategy is needed but not
  explicitly authorized;
- a workbook lock is active or workbook/output restoration cannot be proven;
- current workbook, projection, draft, generated-output, or publication identity
  cannot be reconciled;
- an existing nonterminal draft would be overwritten, rebound, or bypassed;
- a required test owner is unknown, duplicated, stale, or outside the audited CI
  inventory;
- a validation shard reaches the 15-minute cap or loses practical headroom;
- implementation would require starting a later checkpoint to make the current
  checkpoint appear complete.


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

## 3. Baseline diagnosis, resolved defects, and open product debt

The original diagnosis remains historical evidence, but the working plan must
separate defects already resolved by Checkpoint 1 from work that is still open.
At the inspected PR 37 baseline:

| # | Baseline finding | Current status | Owning checkpoint |
|---|---|---|---|
| 1 | Generic row Edit rendered the form after a 100-row table, outside the viewport. | Primary connected views no longer depend on that interaction. The raw Advanced & Recovery browser still uses a below-table generic editor and is not the target experience. | 3 |
| 2 | `/api/structure/{model_key}` joined only the model-specific `section_presentation` subset and reported false `no sections mapped` results. | Open. The endpoint still assembles steps primarily from `form_steps`, `section_presentation`, and `form_sections`; the complete runtime graph is not yet the primary source. | 4 |
| 3 | No option- or group-centered relationship view existed. | Resolved for read-only use. Connected option, group, section, and rule endpoints and one typed search now exist. | 1 complete |
| 4 | Group lists led with hash-like canonical IDs. | Resolved in the Manager by Checkpoint 2's approved workbook-authored labels. Customer-runtime heading consumption remains gated to Checkpoint 5. | 2 complete; 5 |
| 5 | The display-ID helper could manufacture visually plausible but false names. | Resolved in connected views by factual fallbacks first and approved workbook labels in Checkpoint 2; raw advanced tables may still show canonical identity because they are technical surfaces. | 1 and 2 complete |
| 6 | Customer runtime hardcoded generic group headings. | Open. Workbook-owned group headings and runtime migration remain gated. | 5 |
| 7 | Dense lists repeated ambiguous edit/delete icons and blurred read-only versus editable state. | Partially resolved in primary read-only workspaces. The advanced raw browser intentionally remains technical; contextual primary editing is not implemented. | 3 |
| 8 | First-run and stale projection surfaced lifecycle errors instead of a controlled state. | Resolved for the Checkpoint 1 readiness shell; later checkpoints must preserve it. | 1 complete |
| 9 | Import, backup, refresh, and other unrelated actions appeared as equivalent peers. | Partially resolved. The normal shell is clearer; remaining maintenance and Review & Apply terminology must be audited as their checkpoints change. | 5 and 6 |
| 10 | Browser checks did not prove visibility, focus, navigation, narrow layout, or expected-error containment. | Improved in Checkpoint 1 with headless-browser evidence. Durable regression ownership must accompany every later interactive checkpoint. | Every implementation checkpoint |
| 11 | Writable fields without explicit type/enum/reference metadata silently became `free_text`. | Open. `_schema_dict()` still starts from `field_kind = "free_text"`, and `RecordForm` still renders the generic fallback. | 3 |
| 12 | Raw rows exposed purposeless comparison checkboxes and an arbitrary two-row diff. | Resolved. The separate workbook review export remains. | 1 complete |

The hardened plan also recognizes these relational-product gaps observed in the
current implementation:

13. Search performs application-side ranking and can issue per-group member
    queries. It needs batched relational assembly, stable filtering, and a query
    budget before the dataset or diagnostic catalog grows.
14. Connected entity state is component-local. The selected entity, search,
    origin, and expanded context are not durable URL/browser-history state.
15. Connected detail shows only the disposable projection. It does not overlay
    active draft intent, pending addition/deletion, or direct impact.
16. The primary navigation still lacks the specified **Sections & Layout**
    workspace; Form Overview and raw structure tools remain the only entry.
17. Reference controls download generic record lists and show canonical values
    without a dedicated bounded human-label option contract.
18. Human Review & Apply summaries are not yet the primary grouping model for
    every operation family.

The verified projection and canonical workbook may still be healthy while these
product defects exist. The recovery must not treat UI difficulty as permission
to rewrite workbook data or bypass the existing durable workflow.

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

### 4.7 One canonical relational identity

Every connected destination uses one stable identity tuple:

```text
(scope, model_key, entity_type, canonical_id)
```

`scope` is `model` for model-owned entities and `global` only for an explicitly
shared workbook entity. `entity_type` distinguishes exclusive groups from rule
groups even when their textual IDs collide. Labels, RPOs, source rows, and
search text never replace canonical identity.

### 4.8 Projection is evidence; draft overlay is intent

The disposable projection describes the last verified workbook import. Durable
draft operations describe proposed intent. Connected workspaces may present an
**effective preview** by overlaying draft operations on projection records, but
they must label base, proposed, and effective values and must never mutate the
projection to simulate a save.

### 4.9 The backend owns relationship assembly

React may render, filter already returned rows, and preserve navigation state.
It must not independently join option, availability, group, rule, pricing,
override, default, section, or asset records and must not reproduce rule or
validation semantics. One backend relational assembler owns each connected
read model and exposes lineage for every relationship.

### 4.10 Primary workflows are semantic, not generic CRUD

The normal Manager exposes actions such as `Edit option`, `Add option to group`,
`Move member`, or `Change section placement`. It does not ask the operator to
choose a SQL table and row. The generic record browser remains an advanced
traceability/recovery tool and is never the only path for a promoted primary
workflow.

### 4.11 Bounded, inspectable behavior

Search, connected detail, diagnostics, reference lookup, and impact analysis
must be bounded by explicit limits, stable ordering, and query-count tests.
Performance must not be obtained by hiding relationships or moving business
logic into the browser.

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

### 5.3 URL and browser-history contract

The application must preserve connected navigation without adding a routing
dependency unless separately approved. The current single-page application may
use `window.history.pushState`, `replaceState`, query parameters, and the
`popstate` event.

The canonical navigable state is:

```json
{
  "model": "stingray",
  "workspace": "options",
  "type": "option",
  "id": "opt_example",
  "origin": "search",
  "query": "5ZU",
  "diagnostic": "",
  "expanded": "groups"
}
```

The URL must encode at least `model`, `workspace`, `type`, and `id` when an
entity is open. Search text, diagnostic key, and expanded panel may be encoded
when doing so improves return behavior. Browser Back/Forward restores the prior
model, workspace, selected entity, result list, and meaningful focus target.
Reloading a valid deep link opens the same connected entity after readiness is
resolved. Invalid or stale deep links show a bounded not-found state and a
single safe return action; they do not fall through to a raw table.

### 5.4 Persistent model and draft context

The selected model belongs in the application header and is shared by every
primary workspace. A workspace may repeat the model label for clarity but must
not maintain an independent model state. The header also exposes the active
draft identity/status and change count through one persistent draft tray or
summary control.

Changing models while an entity is open must:

1. update the URL and global model state;
2. cancel or ignore stale in-flight responses from the prior model;
3. attempt to resolve the same semantic destination only when canonical identity
   is valid in the new model;
4. otherwise return to the destination workspace with an explanation;
5. preserve the durable draft rather than silently creating or switching drafts.

### 5.5 Workspace capability contract

Every workspace receives backend-derived capabilities such as:

```json
{
  "inspect": true,
  "edit": false,
  "add": false,
  "deactivate": false,
  "reorder": false,
  "blocked_reason": "Checkpoint 3 not authorized"
}
```

Capability is based on workbook ownership, projection readiness, draft status,
and checkpoint implementation—not on whether a component happens to render an
icon. A blocked capability is visually distinct from permanently read-only
content.

### 5.6 Default landing and empty states

After readiness, Form Overview is the default. Empty search, no-results,
zero-member, no-rule, no-price, no-image, and unmapped-section states each use a
specific explanation and next action. They must not reuse one generic `No data`
message because absence can mean valid none, unsupported model scope, stale
projection, incomplete workbook data, or a filtered result.

## 6. Relational Explorer and connected read-model contract

### 6.1 Entity identity and scope

The initial primary connected entity types are:

- `option` — identity `(model_key, option_id)`;
- `exclusive_group` — identity `(model_key, group_id)`;
- `rule_group` — identity `(model_key, group_id)`;
- `section` — model-scoped presentation of a globally identified `section_id`;
- `rule` — identity `(model_key, rule_id)`.

Supporting entities—variant, pricing rule, default rule, asset, runtime step,
interior, and draft operation—may be linked or summarized without becoming
primary workspaces until a checkpoint promotes them. A response never implies
that the same RPO or textual ID in another model is the same canonical entity.

Frontend destinations use an explicit type; the `group` convenience type used
by Checkpoint 1 must normalize to `exclusive_group` or `rule_group` before
editing, impact analysis, or URL serialization.

### 6.2 Relationship vocabulary

Connected read models use a stable, directional relationship vocabulary. Each
edge includes a deterministic relationship identity, source and target entity
identities, model scope, active/effective state, human summary, and workbook
lineage.

| Relationship | Source → target | Authoritative projected family |
|---|---|---|
| `placed_in` | option → section | `options.section_id` plus complete form graph |
| `available_in` | option → variant | `option_availability` |
| `member_of_exclusive_group` / `contains_option` | option ↔ exclusive group | `exclusive_group_members` |
| `member_of_rule_group` / `contains_target` | option/interior ↔ rule group | `rule_group_members` |
| `rule_group_source` | option/interior → rule group | `rule_groups.source_id` |
| `includes` | source → target | `rule_mappings.rule_type=includes` |
| `requires` | source → target | `rule_mappings.rule_type=requires` |
| `excludes` | source → target | `rule_mappings.rule_type=excludes` |
| `replaces` | source → target | `rule_mappings.runtime_action=replace` with exact source evidence |
| `conditions_price` | option/interior → pricing rule | `pricing.condition_option_id` |
| `priced_by` | pricing rule → option/interior | `pricing.target_option_id` |
| `overridden_in` | option → variant | `variant_option_overrides` |
| `defaulted_by` | default rule → option | `default_selection_rules` |
| `covered_by_asset` | option/shared target → asset | `assets` / shared asset reconciliation owner |

The assembler must not collapse distinct workbook rows merely because their
plain-language summaries match. Reciprocal edges may share one source-row
identity but must retain direction. Unsupported or unresolved references remain
traceable findings rather than disappearing from the relation set.

### 6.3 Additive response envelope

Current Checkpoint 1 routes remain valid while later checkpoints migrate the
frontend. New response members are additive; existing members are not renamed
or removed until callers and tests migrate in one reviewed checkpoint.

A connected response must converge on this envelope:

```json
{
  "schema_version": "workbook-manager-connected-2",
  "model_key": "stingray",
  "projection": {
    "state": "current",
    "workbook_sha256": "…",
    "projection_source_sha256": "…"
  },
  "entity": {
    "type": "option",
    "id": "opt_example",
    "label": "5ZU — Black Exhaust Tips",
    "active": true
  },
  "relationships": {},
  "relationship_counts": {},
  "draft_overlay": {
    "draft_id": "",
    "draft_revision": 0,
    "state": "unchanged",
    "base": null,
    "proposed": null,
    "effective": null,
    "conflicts": []
  },
  "capabilities": {},
  "navigation": {
    "destination": {},
    "canonical_url_state": {}
  },
  "technical": {
    "canonical_id": "opt_example",
    "lineage": []
  }
}
```

`projection` identifies the data actually read by the request, not a later
status response. `lineage` contains source sheet, row, family, physical key, and
model context for the entity and each edge. Technical identity is expandable in
the UI and never omitted from API evidence.

### 6.4 Search and filtering

Search is model-scoped and typed across options, exclusive groups, rule groups,
sections, and rules. It accepts a trimmed query of 1–200 characters and a limit
of 1–100. Blank input returns no result query.

Ranking is deterministic:

1. exact RPO;
2. exact canonical ID;
3. exact approved human label or option name;
4. RPO/label/ID prefix;
5. token-prefix match;
6. descriptive contains match.

Ties sort by entity-type priority appropriate to the current workspace, human
label, then canonical ID. Search results include:

- explicit entity type and canonical destination;
- human primary label and a secondary context label;
- active/inactive state;
- section or group type where applicable;
- small relationship counts when they can be supplied without an N+1 query;
- whether the entity has active-draft changes;
- exact rank reason in Technical details for testability.

The UI provides typed filters for entity type and active state. Section,
variant, and diagnostic-origin filters may be added when backed by the same
server contract. The Groups workspace may default to group results, but the
underlying search endpoint must not create a separate group-only truth model.

Search implementation must batch group/member facts. It must not execute one
member query per result and must not re-read the workbook. A current-projection
SQLite query, a bounded set of batched queries, or a projection-bound index is
acceptable.

### 6.5 Connected option detail

The option workspace shows coordinated panels from one HTTP response:

- **Overview:** RPO, name, customer copy, section and step, base price,
  selectable/display behavior, active state, and customer-form preview where
  practical.
- **Availability:** every selected-model variant in display order, explicit
  standard/available/unavailable status, missing status, and variant override.
  Inherited and overridden values are visibly distinct.
- **Groups:** all exclusive and rule groups in which the option is a member,
  target, or source, with behavior, member count, active state, and connected
  destination.
- **Rules:** every incoming and outgoing includes/requires/excludes/replaces
  edge, including body/trim/variant scope and disabled reason.
- **Pricing:** base price and every rule for which the option is condition or
  target, with human source/target labels and exact amount/type.
- **Defaults and overrides:** default-selection and variant override records.
- **Images:** exact and shared coverage, active state, fit/position/hover facts,
  and a link into the existing reconciliation owner.
- **Draft impact:** active-draft base/proposed/effective values and direct
  dependent records that validation will reconsider.
- **Technical details:** canonical identity, all source rows, physical ownership,
  model context, and projection fingerprints.

A panel with zero valid relationships states that fact. A failed or unsupported
join is not rendered as a valid zero count.

### 6.6 Connected group, section, and rule detail

An exclusive-group workspace shows human label status, selection behavior,
notes, active state, ordered members, section/form usage, customer heading and
instruction preview, draft changes, direct dependents, and lineage.

A rule-group workspace additionally shows source entity, group type, scope,
ordered targets, disabled reason, incoming references, and a plain-language
relationship sentence. It must not pretend that a rule group is a
customer-visible exclusive-choice heading unless the workbook/runtime contract
says so.

A section workspace shows master identity, effective model presentation,
resolved runtime step or bucket, ordered options, context/summary mappings,
draft overlay, and fresh-runtime parity evidence. `form_sections` remains
read-only; editable presentation records identify their actual writable family.

A rule workspace shows type/action, source, target, scope, disabled reason,
original source detail, linked option/interior entities, draft overlay, and
lineage. Rule sentences are derived from registered semantics, not free-form AI
summaries.

### 6.7 Stable navigation and return context

Every normal entry point resolves to the same typed workspace. Opening an
option from Form Overview, Sections & Layout, a group member, a rule, pricing,
Images, search, a diagnostic, or Review & Apply must produce the same entity
identity and effective read model.

Navigation records an origin frame containing model, workspace, query/filter,
scroll anchor, selected entity, and expanded panel. `Back to results` restores
that frame. Browser Back/Forward and a direct deep link produce equivalent
state. Focus returns to the initiating result or relationship when it still
exists; otherwise it moves to the workspace heading with an explanation.

### 6.8 Draft overlay and direct impact

Connected routes accept an optional active `draft_id`. The backend overlays
coalesced durable operations without modifying the projection and returns one of:

- `unchanged`;
- `modified`;
- `added`;
- `pending_deletion`;
- `conflicted` because the draft binding or projection fingerprint is stale.

For modified records the UI can compare base, proposed, and effective values.
For added entities the workspace can resolve the proposed record even though no
projection row exists. Pending deletion remains inspectable with a prominent
status and dependent-impact panel. A stale or conflicted overlay never appears
as current.

Direct impact includes:

- rows that reference the edited entity through registered references;
- variants, groups, sections, rules, pricing, defaults, overrides, and assets
  whose validation result may change;
- promoted model outputs ownership-derived from the draft operation set;
- whether the operation changes customer-visible copy or runtime structure.

Impact analysis is explanatory and bounded. It does not grant write authority
and does not replace exact final-graph preview.

### 6.9 Named diagnostic contract

Each diagnostic declares:

```json
{
  "key": "multiple_exclusive_groups",
  "label": "Options in more than one exclusive group",
  "definition": "…",
  "scope": "model",
  "required_entity_type": null,
  "result_entity_types": ["option"],
  "read_only": true
}
```

The five Checkpoint 1 diagnostics remain required:

- options without required image coverage;
- options belonging to more than one exclusive group;
- where an option or group is used;
- all incoming/outgoing option relationships;
- availability that differs by variant.

After the complete graph and label contract exist, add deterministic integrity
views for:

- active group with zero active members;
- active group member or rule targeting a missing/inactive entity;
- option placed in a missing or unresolved section;
- duplicate member display order inside one active group;
- runtime-visible exclusive group without an approved display label;
- draft operation whose projection/workbook binding is stale.

These views report exact definitions and evidence. Terms such as `suspicious`,
`bad`, or `should` are prohibited unless a validator already owns that judgment.
Results are paginated, stably sorted, deep-linkable, and carry the projection
fingerprint used to compute them.

### 6.10 Query, response, and performance bounds

Search and connected detail must be bounded and regression-tested for query
count, not left unbounded. The first implementation of each endpoint measures a
warm-projection baseline and records it in this section; the recorded count then
becomes the hard regression ceiling for that endpoint until a later spec
revision records evidence for a different bound. A measured baseline is
authoritative over any pre-assigned number.

One endpoint must not trigger browser-side follow-up requests for each returned
relationship (no N+1 assembly). Default detail arrays are bounded; larger
member/result sets use server pagination with total count and stable order.

A warm local benchmark against the canonical workbook should keep ordinary
search and entity-detail latency within an operator-acceptable range recorded
alongside the baseline. This is an operator target and a controlled benchmark
assertion, not a flaky shared-runner wall-clock gate. SQL query count, response
shape, and result completeness are hard tests.

## 7. Group Manager and workbook-owned labels

### 7.1 Implemented workbook contract

Checkpoint 2 implemented a `display_label` column for the registered
`exclusive_groups` and `rule_groups` families. Customer-runtime heading
consumption remains separately gated to Checkpoint 5.

Implemented shape:

- column name: `display_label`;
- physical position: immediately after `group_id` in each registered family;
- `group_id` remains immutable canonical identity;
- `display_label` is deliberate human copy, never generated from a hash;
- active customer-rendered exclusive groups require an approved nonblank label;
- rule-group labels are Manager-facing unless a separate runtime contract makes
  them customer-visible;
- `notes` remains internal/explanatory prose and is never parsed or promoted;
- the registry, workbook schema validator, importer/projection, editor schema,
  generator, generated contract, and Manager consumer agree on ownership;
- missing or invalid labels fail the appropriate migration/generation gate; they
  do not silently fall back in the completed contract.

### 7.2 Label validation rules

An approved display label must:

- be trimmed, single-line Unicode text;
- contain 3–100 visible characters, the registry-owned validation bound
  implemented in Checkpoint 2B;
- not equal its canonical `group_id`;
- not equal a placeholder such as `Related options`, `Unnamed group`, or
  `Label pending workbook review`;
- not contain the terminal hash token from a hash-like canonical ID;
- not be derived automatically from notes, member names, or IDs;
- be appropriate for the stated audience (`manager` or `customer`);
- remain separate from selection instructions such as `Choose one` or
  `Selection required`.

Duplicate labels are not globally forbidden because context can differ, but two
customer-visible groups with the same label in the same model and runtime step
require explicit reviewer confirmation and a recorded rationale.

### 7.3 Required migration review artifact

Checkpoint 2 must generate both:

- `workbook-manager/review/group-display-label-review.csv` for human review;
- `workbook-manager/review/group-display-label-review.json` as the exact
  machine-readable companion.

Each active and inactive existing group has one row/object with:

- `model_key`;
- `group_type` (`exclusive` or `rule`);
- `group_id`;
- current factual Manager fallback label;
- source sheet and row;
- active state;
- runtime/customer-visible classification;
- resolved step and section context where available;
- selection/rule behavior;
- member count and ordered member RPOs/names;
- notes shown as evidence only;
- `proposed_display_label`;
- `audience` (`manager`, `customer`, or `not_rendered`);
- `review_status` (`pending`, `approved`, `revise`, or
  `not_customer_rendered`);
- `reviewer_note`;
- artifact schema version and source workbook SHA-256.

Proposal generation may use deterministic context to assemble evidence, but it
must leave `proposed_display_label` blank when no authoritative label exists.
It may not auto-approve a proposal. Artifact ordering is stable by model,
group type, source sheet/row, and group ID.

### 7.4 Approval and write separation

Checkpoint 2 has two mandatory stops:

1. After the schema/registry proposal and complete review artifact are ready,
   stop for explicit approval of the actual labels and classifications.
2. After approved labels are written and regenerated artifacts pass, stop before
   changing customer-runtime headings; that switch belongs to Checkpoint 5.

The workbook write must use the existing guarded path, backup, package/schema
validation, semantic readback, affected-model generation, registry publication,
and rollback evidence. A partially approved label set may be stored in the
review artifact but may not be partially published to customer runtime.

### 7.5 Customer runtime presentation

For a visible exclusive group, the completed customer form renders:

```text
Engine cover choices
Choose one
```

or:

```text
Performance brake options
Selection required
```

The heading comes from approved workbook `display_label`; the instruction comes
from registered selection semantics. The generic `Related Options` heading is a
temporary pre-migration fallback only and is removed after the all-model
Checkpoint 5 gate.

### 7.6 Group workspace

The Groups workspace supports search/filter by label, type, step/section,
active state, behavior, member count, missing-label state, and active-draft
state. Each result leads with the human label or factual pending-label state and
shows canonical identity only in Technical details.

Connected detail shows:

- label status and audience;
- group type and registered behavior;
- notes;
- ordered active/inactive members as `RPO — Option Name`;
- source option for rule groups;
- step/section/form usage;
- incoming and outgoing references;
- customer heading/instruction preview when applicable;
- direct draft overlay and impact;
- source sheet/row and physical identity.

### 7.7 Contextual group editing

Within the existing durable draft lifecycle, an authorized group editor may:

- edit approved fields through registry-driven controls;
- add an existing valid option/interior target through a bounded reference
  selector;
- remove a member after showing direct dependents and final-graph risk;
- reorder members with deterministic display-order normalization;
- activate/deactivate a group or member when the registered contract permits;
- open a member's connected workspace and return to the same group/editor state.

Member reordering supports pointer and keyboard interaction. The resulting
operation set must produce unique deterministic `display_order` values without
rewriting unrelated members when a smaller bounded change is possible. The UI
shows the exact proposed order before Save.

Adding a new group remains blocked until a separately approved canonical-ID
allocation strategy is recorded. The UI must not ask an operator to invent a
hash-like ID. Editing or adding membership does not require a new ChangeSet
dialect; it emits ordinary existing parent/member draft operations.

## 8. Complete form graph and Sections & Layout contract

### 8.1 Graph ownership

The model-specific form graph is a connected read model assembled from:

- `form_steps` / `runtime_steps_meta`;
- read-only `form_sections` from `section_master`;
- writable `section_presentation`;
- `context_sections`;
- `order_summary_sections`;
- `step_order_summary_map`;
- option placement through `options.section_id` and variant overrides;
- fresh generated runtime metadata as the parity oracle.

No single table is the graph. React must not recreate the join.

### 8.2 Deterministic assembly sequence

For one selected model the backend:

1. loads active and inactive runtime steps in registered order;
2. loads every section referenced by options, presentation, context, or summary
   mappings;
3. merges model presentation onto section master identity;
4. resolves effective `step_key` from model presentation when present, otherwise
   from the authored master relationship when supported;
5. attaches ordered options and variant-specific placement overrides;
6. classifies ordinary sections, context sections, standard-equipment buckets,
   auto-added buckets, summary-only mappings, hidden/conditional records, and
   true unmapped records;
7. records source evidence and any disagreement instead of discarding one side;
8. compares the assembled graph with freshly generated runtime metadata for
   promoted models.

### 8.3 Form-graph response

Add an additive connected endpoint such as
`GET /api/explorer/{model_key}/form-graph` unless live routing evidence supports
a clearer equivalent. It returns:

- projection/workbook identity;
- ordered step nodes;
- section/bucket nodes with type and effective presentation;
- ordered option references;
- context and summary edges;
- draft overlay;
- parity findings with expected/actual source evidence;
- counts for active, hidden, bucket, context, summary-only, and unresolved nodes.

`No sections mapped` is valid only when the complete graph has no effective
section/bucket/context edge for that step. A standard-equipment bucket is shown
as a bucket, not as a broken step.

### 8.4 Sections & Layout workspace

Add **Sections & Layout** to primary navigation. The workspace presents:

- runtime sequence with drag/keyboard-safe ordering only where editing is
  authorized;
- ordinary sections and customer labels;
- standard-equipment and auto-added buckets;
- context and summary mappings;
- active/hidden/conditional status;
- options placed in each section;
- draft changes and parity findings;
- a connected section detail destination.

The operator can filter to unresolved mappings, empty sections, inactive
records, buckets, or draft changes without leaving the graph.

### 8.5 Section editing ownership

`form_sections` remains read-only. Contextual section editing writes only the
registered writable family that owns the requested change, such as
`section_presentation`, `runtime_steps_meta`, `context_section_master_meta`,
`order_summary_sections_meta`, or `step_order_summary_map_meta`.

The editor states which workbook family will change and distinguishes:

- customer label versus canonical section identity;
- runtime step placement;
- section display order;
- display behavior;
- standard-equipment/auto-added bucket semantics;
- active state;
- notes;
- option placement owned by the option or override family rather than the
  section master.

Every effective graph change remains draft-only until exact preview, approval,
and Apply and Rebuild.

## 9. Editable, read-only, blocked, and destructive visual contract

### 9.1 Editable content

Editable content has a named affordance such as `Edit option`, `Edit group`, or
`Edit section`. A card/row may open inspection, but editing requires a separate
semantic action. Icons may supplement text but do not replace the accessible
name for primary or destructive actions.

### 9.2 Read-only content

Read-only content:

- shows `Reference only` and, where useful, its authority;
- omits Edit, Delete, Add, and empty Actions columns;
- uses a quieter but legible surface;
- remains navigable when it has a connected destination;
- never displays disabled destructive icons that imply a hidden unlock path.

### 9.3 Temporarily blocked content

Normally editable content blocked by stale projection, immutable draft state,
active import/promotion, recovery, or unresolved binding shows `Editing
blocked`, the exact cause, and one safe recovery action. It is not styled as
permanently read-only.

### 9.4 Editor drawer/sheet

Contextual editing uses one reusable shell:

- desktop: right-side drawer, visible within the current viewport;
- narrow viewports: full-screen sheet;
- `role="dialog"`, meaningful accessible heading, and modal semantics when the
  background is not interactive;
- initial focus on the heading or first invalid/meaningful field;
- focus containment, Escape handling when safe, and focus return to the
  initiating control;
- sticky Save/Cancel footer; neither action may be below an unbounded record
  list;
- background scroll containment without trapping the user after close;
- unsaved-change confirmation when close would discard local edits;
- visible draft effect and target family before Save.

No new modal/drawer dependency is introduced without approval; the existing
React/CSS stack is sufficient unless proven otherwise.

### 9.5 Entity and draft states

Cards, details, search results, and draft rows distinguish at least:

- unchanged projection record;
- modified in active draft;
- added in active draft;
- pending deletion;
- inactive workbook record;
- blocked/conflicted overlay;
- applied historical evidence.

Color is never the sole signal. Text and iconography identify each state.

### 9.6 Destructive and ordering actions

Delete/deactivate actions live inside selected-entity context or a clearly
labeled overflow. Confirmation names the entity and distinguishes physical
row deletion from active-state deactivation. Direct dependents are shown before
the operation is saved; final-graph preview remains authoritative.

Reorder controls state the collection being reordered, support keyboard use,
and show the proposed final order. A generic row checkbox is not a reorder or
bulk-edit contract.

## 10. Registry-driven editing controls and mutation contract

### 10.1 Complete field classification

Every field named by registry-owned `WRITABLE_COLUMNS` must have explicit
control metadata. Absence of metadata is an error, never an implicit free-text
choice.

Extend each family in
`scripts/corvette_form_generator/workbook_domain/registry.py` with a `controls`
mapping rather than creating a parallel frontend list. A normalized entry is:

```python
"price": {
    "kind": "money",
    "label": "Base price",
    "group": "Pricing",
    "order": 10,
    "blank": "forbidden",
    "min": 0,
    "step": 1,
    "help": "Whole-dollar MSRP contribution.",
    "affects": ("pricing", "customer_total"),
}
```

Required `kind` values are:

- `boolean`;
- `finite`;
- `reference`;
- `integer`;
- `money`;
- `url`;
- `structured_text`;
- `short_text`;
- `long_text`;
- `immutable` / `generated` / `read_only`.

Open text is valid only when deliberately classified. Every metadata entry also
defines label, field group, ordering, blank semantics, help text, and impact
categories. Kind-specific metadata defines finite-value source, reference
scope, discriminator, numeric bounds/step, pattern, multiline behavior, or
creation strategy.

### 10.2 Registry and API invariants

The registry remains authoritative for writable columns, type, enum/reference
semantics, optionality, and control metadata. The Manager adapter may add
routing and presentation facts but not override allowed values.

`_schema_dict()` must fail closed when:

- a writable field has no control metadata;
- metadata kind contradicts registered type/enum/reference data;
- a reference target/scope cannot be resolved;
- blank/required behavior disagrees with registry validation;
- a key is editable during update;
- a generated/read-only field is included in a mutation payload;
- a projected read-only family exposes a column with no control metadata, or
  with a control kind other than `read_only`.

Read-only projections (`form_sections`) are graded against the read-only
contract above, never against the writable inventory. Exempting them from
validation entirely would let a projected column ship with no control metadata
at all, which is the failure this section exists to prevent.

The schema response exposes normalized metadata and a schema version. React has
one renderer map keyed by `kind`; it has no generic fallback to `<input
class="text">`.

### 10.3 Required control behavior

- Boolean fields distinguish `Yes`, `No`, and `Not specified / inherit` when
  blank is valid. SQL/internal values remain in Technical details.
- Small finite domains use radio/segmented/select controls; larger domains use a
  searchable combobox. Submission outside the registered domain is impossible.
- References lead with human labels and show canonical ID secondarily. Model
  scope and union family are enforced by the server.
- Conditional references refresh when the discriminator changes. An obsolete
  value is visibly cleared with explanation or blocks Save; it is never silently
  treated as valid.
- Integer, money, order, priority, URL, position, and structured fields use
  purpose-specific input and inline validation.
- Long-form copy/notes use text areas with existing format/length guidance.
- Immutable keys remain locked on edit. Add flows use only an approved creation
  strategy.

An existing value outside the registered domain is rendered as `Current value
is not valid for this field`. It is not appended as an apparently valid option.
The exact legacy value remains visible in Technical details and Save requires an
approved replacement or compatibility rule.

### 10.4 Bounded reference-option API

Do not populate reference fields by downloading up to 2,000 generic records for
each field. Add one internal, additive endpoint, or a demonstrably equivalent
contract, that accepts:

- source table/family and field;
- selected model;
- query text;
- discriminator value when conditional;
- limit (default 25, maximum 100);
- optional cursor/offset.

It returns:

```json
{
  "schema_version": "workbook-manager-reference-options-1",
  "field": "section_id",
  "scope": "model",
  "query": "paint",
  "total": 3,
  "options": [
    {
      "value": "sec_pain_001",
      "label": "Exterior Color",
      "secondary": "sec_pain_001",
      "active": true
    }
  ]
}
```

The endpoint derives choices from registry targets and the current projection,
uses stable ordering, and follows the query budget in §6.10. It does not expose
an arbitrary table browser as a combobox API.

### 10.5 Client and server validation timing

Control-level validation runs on change/blur and before Save. Errors name the
field, accepted choice/format, and correction. Backend operation validation and
final-graph preview remain authoritative.

The Save control is disabled while one request is active. A client-generated
operation token or existing durable coalescing identity prevents accidental
double-save from producing duplicate intent. The response returns the current
draft revision and effective operation state. When the client submits against a
stale draft revision or projection binding, the server returns a conflict with
an exact reload/reconcile action rather than accepting ambiguous intent.

### 10.6 Contextual editor field groups

The option editor groups fields by operator intent:

1. identity and customer copy;
2. form placement and display;
3. availability;
4. groups and relationships;
5. pricing/defaults/overrides;
6. images;
7. technical ownership.

The group editor groups:

1. label/audience and behavior;
2. members and order;
3. form usage and impact;
4. active state and notes;
5. technical ownership.

The section editor groups:

1. customer label and status;
2. step placement and ordering;
3. bucket/context/summary behavior;
4. contained options and impact;
5. technical ownership.

The initial drawer may implement a bounded subset, but it must explicitly label
unimplemented fields read-only; it may not fall back to raw text editing.

### 10.7 Section Presentation minimum matrix

| Field | Required control |
|---|---|
| `section_id` | Human-label reference selector; canonical ID secondary; immutable on edit. |
| `step_key` | Bounded selector over proven runtime-step/bucket targets for the model. |
| `display_behavior` | Optional finite selector from generator/runtime authority. |
| `standard_equipment_bucket` | Explicit optional Boolean/three-state control. |
| `standard_equipment_group_type` | Optional finite selector only after the complete domain is proven. |
| `auto_added_bucket` | Explicit optional Boolean/three-state control. |
| `section_display_order` | Constrained integer/order control. |
| `active` | Explicit Boolean control. |
| `display_label` | Deliberate short text. |
| `notes` | Deliberate long text. |

The same exhaustive proof applies to every writable family. Passing this one
example is insufficient.

### 10.8 Completeness test

Generate a test matrix directly from `WRITABLE_COLUMNS` and registry controls.
The gate fails for missing metadata, contradictory kind, unrestricted rendering
of a constrained field, invalid reference scope, duplicated frontend values,
blank/required mismatch, or a new writable column with no deliberate control.
The test reports family and field so the failure is immediately actionable.

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

### 11.1 Purposeful member and bulk selection

A member-management surface may introduce selection only for a named operation
such as `Remove selected members from draft`. It must:

- show eligible entity type and scope;
- display a persistent selected-count/action bar;
- exclude invalid/inactive targets when required by contract;
- support keyboard selection;
- clear or confirm selection when model/group/context changes;
- preview the exact operation set before Save.

Drag handles, move-up/down controls, or ordered list interaction are preferred
for reordering; unrelated row checkboxes are not used.

## 12. Action naming and operational clarity

Every operation names its target and outcome. The completed UI uses these terms
unless implementation evidence supports a clearer exact variant:

| Current/technical label | Required operator label | Meaning |
|---|---|---|
| `Re-Import Workbook` | `Reload Latest Workbook Data` | Verify the canonical workbook and replace only the disposable browsing projection. |
| `Backup Manager State` | `Back Up Drafts & History` | Copy durable Manager workflow/recovery state; does not back up or change the workbook. |
| `Refresh` | Remove, or `Refresh Screen Status` when a manual reread is proven necessary | Reread status only. |
| `Refresh inventory` | `Refresh WordPress Image Inventory` | Refresh read-only media inventory/reconciliation; does not change WordPress media. |
| `Export Disposable Comparison` | `Export Workbook Review Copy` | Create a non-authoritative review workbook that cannot become canonical. |
| `Freeze ChangeSet` | `Lock Draft for Validation` | Bind the exact mutable draft into one immutable ChangeSet. |
| `Preview ChangeSet` | `Validate Draft Against Workbook` | Run exact final-graph validation without writing. |
| `Approve Exact Preview` | `Approve Validated Changes` | Approve only the exact successful preview; does not write. |
| `Apply and Rebuild` | `Write Approved Changes & Rebuild Form Data` | Back up, write, verify, regenerate affected local model data, and publish the local registry; does not deploy or submit. |
| `Cancel Draft` | `Cancel Draft and Keep Audit Record` | End the draft while retaining immutable history. |

Contextual editor verbs are entity-specific:

- `Save option change to draft`;
- `Save group changes to draft`;
- `Add option to group draft`;
- `Save member order to draft`;
- `Save section placement to draft`;
- `Deactivate <entity> in draft` or `Delete <entity> row in draft`, whichever is
  physically accurate.

The control and adjacent explanatory text state that Save changes durable draft
intent only. Unrelated maintenance actions are grouped under Advanced &
Recovery by target: workbook data, drafts/history, image inventory, review
exports, and system status. No screen presents unrelated actions as equivalent
peers.

## 13. First-run, freshness, error, and recovery experience

### 13.1 Readiness state decision table

Before normal workspaces render, the application resolves one state from
current status evidence:

| UI state | Required condition | Primary action | Permitted behavior |
|---|---|---|---|
| `Starting Workbook Manager` | Initial boot before status result | None | Shell/status only. |
| `Loading and checking workbook data` | Import/promotion or initial verification in progress | None or cancel only where supported | No stale/empty primary tables. |
| `Ready to edit` | Workbook and projection current; no blocking recovery state; draft mutable or absent | Contextual work action | Read and authorized draft editing. |
| `Draft requires attention` | Current projection plus nonterminal draft needing resume/review | `Resume draft` / `Review draft` | Bound draft actions only. |
| `Workbook changed—reload latest data` | Workbook identity differs from projection | `Reload Latest Workbook Data` when no blockers | Inspection of status/technical evidence; editing blocked. |
| `Workbook recovery required` | Missing/unverified projection, unresolved legacy work, unknown apply/restore, or incompatible draft binding | Exact recovery action | No ordinary editing/apply. |
| `Cannot reach Manager backend` | Status request failed after bounded retry | `Retry connection` | Static explanation only. |

Promotion-reader or durable-lock `503` responses remain bounded busy states and
must not be mislabeled as workbook corruption.

### 13.2 Client request ordering

Model, workspace, search, diagnostic, and entity changes cancel prior fetches
with `AbortController` or ignore stale responses using a monotonically
increasing request token. A late prior-model response must never replace current
state. Loading indicators attach to the control/panel that initiated the
request rather than blanking the entire application when other current content
is safe.

### 13.3 Expected lifecycle states

A locally created draft ID that has not persisted does not trigger a visible 404.
Known stale projection state prevents asset/editor requests instead of emitting
a cascade of expected 409 errors. Expected 404/409/503 states are translated to
the readiness or entity-not-found contract and do not fill the console during a
successful recovery path.

### 13.4 Error envelope

New or modified Manager endpoints converge on this additive error detail:

```json
{
  "status": "projection_not_current",
  "message": "Workbook data changed after this draft was created.",
  "affected_surface": "draft",
  "workbook_changed": false,
  "safe_next_action": {
    "label": "Review draft recovery",
    "action": "open_recovery"
  },
  "request_id": "…",
  "errors": [],
  "technical": {}
}
```

The UI always states what failed, what remained unchanged, whether the canonical
workbook changed, and the exact safe next action. Technical code/detail remains
expandable. Generic `Something went wrong` is not sufficient.

### 13.5 Persistent operation results

Import, backup, inventory refresh, validation, approval, cancellation, apply,
and recovery results persist beside their initiating operation until the user
dismisses them or a named state transition supersedes them. An unrelated status
refresh cannot clear a success/failure message or appear to repair a warning.

### 13.6 Entity and deep-link failures

A valid model with a missing entity shows `This entity no longer exists in the
current workbook projection`, its requested identity, and return/search actions.
A model mismatch states that the entity is not present in the selected model.
Neither condition opens an arbitrary raw record or silently changes models.

## 14. Draft tray, Review, and Apply experience

### 14.1 Persistent draft tray

The primary shell exposes the active draft at all times when readiness permits.
The tray shows:

- human draft status;
- operation count and affected entity count;
- affected models;
- counts for added, modified, pending-deletion, asset, and conflicted intent;
- current projection/workbook binding state;
- `Review draft`, `Resume editing`, or the one lifecycle-authorized primary
  action.

Selecting a draft item opens the same connected entity workspace with the draft
overlay and a return path to Review & Apply.

### 14.2 Human summary grammar

Review groups operations by semantic entity and model, not by SQL table. Summary
patterns include:

- `BC4 — Blue LS6 Engine Cover: availability changed for Coupe 2LT from
  Available to Standard`;
- `Engine cover choices: BCP moved from position 3 to position 2`;
- `Exterior accent choices: customer group label changed from … to …`;
- `Exterior Color: option 5ZU moved into this section`;
- `Rule: Z51 now requires … for Convertible`;
- `Price rule …: target price changed from $… to $…`.

The backend owns semantic operation summaries or supplies enough typed metadata
for one shared formatter. Components must not each invent incompatible wording.

### 14.3 Review hierarchy

Review & Apply presents:

1. blocking readiness/binding warnings;
2. human entity/change summaries;
3. direct impact and affected model outputs;
4. exact lifecycle stage and authorized next action;
5. expandable workbook family, sheet/row, physical key, ChangeSet ID,
   fingerprints, immutable attempts, and output-state evidence.

The operator can filter by model, entity type, operation type, warning, or
conflict and can open connected detail without losing review context.

### 14.4 Lifecycle language

```text
edit draft
  -> lock draft for validation
  -> validate against workbook
  -> approve validated changes
  -> write approved changes and rebuild form data
```

Save means durable draft intent only. Locking means immutable ChangeSet emission.
Validation means exact final-graph preview. Approval means exact preview
approval. Only the final typed-confirmation action may write or regenerate.

### 14.5 Apply result and recovery

The completion view separately reports workbook, projection, generated
artifacts, publication, rollback, and next action. A successful write leaves the
projection stale until verified re-import. A downstream failure reports whether
workbook/output restoration was hash-proven. Unknown restoration state exposes
only manual recovery actions.

No browser acceptance uses a live dealer submission, WordPress media mutation,
deployment, or production cache purge.

## 15. Source-of-truth, implementation surfaces, and preserved boundaries

### 15.1 Source-of-truth invariants

- `stingray_master.xlsx` remains canonical for business data, group labels,
  membership, rules, copy, pricing, availability, structure, and asset metadata.
- SQLite remains a disposable verified projection plus durable Manager-owned
  workflow/recovery state; it is not product authority.
- Connected read models may join projection data and overlay durable intent for
  presentation but may not invent outcomes or write around the existing path.
- All edits continue through durable operations, exact ChangeSet, preview,
  approval, guarded apply, rollback, regeneration, and publication.
- Generated artifacts and `form-app/data.js` are outputs, never hand-edited
  fixes.
- No hidden React business rule, alternate ChangeSet dialect, direct workbook
  write, or second asset writer is introduced.

### 15.2 Current implementation map

The coding agent traces the live implementation rather than assuming these
paths are unchanged, but the inspected baseline is:

| Concern | Primary files |
|---|---|
| App readiness/navigation/global context | `workbook-manager/frontend/src/App.jsx`, `styles.css` |
| Connected search/detail/diagnostics | `workbook-manager/backend/app/explorer.py`, `main.py`, `frontend/src/components/ConnectedExplorer.jsx`, `frontend/src/api.js` |
| Registry and Manager schema adapter | `scripts/corvette_form_generator/workbook_domain/registry.py`, `workbook-manager/backend/app/catalog.py`, `main.py::_schema_dict` |
| Generic advanced editing | `frontend/src/components/ModelOperations.jsx`, `RecordForm.jsx` |
| Form structure | `main.py::structure`, `frontend/src/components/FormStructure.jsx` |
| Durable drafts and lifecycle | `backend/app/drafts.py`, `ChangesSync.jsx`, API schemas/routes in `main.py` |
| Guarded apply/rebuild | `backend/app/apply_rebuild.py` and the reliable workflow specification |
| Asset reconciliation | `asset_workspace.py`, `asset_resolutions.py`, `AssetManager.jsx` |
| Manager acceptance | `tests/test_workbook_manager*.py`, `tests/validation_catalog.json`, Release candidate workflow/planner scripts |

### 15.3 Protected boundaries

Unless a separately approved checkpoint explicitly names them, do not change:

- dealer endpoint, payload, security/Turnstile behavior, or submission UX;
- WordPress media upload/delete/rename;
- deployment or production cache purge;
- workbook schema or data;
- generated/runtime contracts or customer headings;
- apply/recovery semantics;
- single-process serving, lock ordering, lifespan bootstrap, or projection gate;
- legacy `POST /api/sync write=true` refusal;
- immutable ChangeSet/preview/approval/apply artifacts.

Checkpoint-specific file permission is not permission to cross these behavior
boundaries.

## 16. Phased implementation runbooks

Each checkpoint is independently authorized, implemented, verified, and closed.
Do not begin the next checkpoint automatically. Within a checkpoint, use the
smallest coherent subpass that leaves a testable product slice and truthful
handoff.

### Checkpoint 1 — readiness shell and read-only connected explorer — complete

Delivered behavior:

- readiness-first shell;
- model-scoped connected option, exclusive/rule group, section, and rule reads;
- typed cross-entity search;
- five named read-only diagnostics;
- entity-specific `where used` and option-relationship controls;
- raw tables/history under Advanced & Recovery;
- arbitrary two-row comparison removed;
- no workbook/schema/generated/customer-runtime write.

Inspected acceptance baseline:

- focused API/shell and headless-browser checks passed;
- prior local Manager acceptance: 185 passed, 2 intentional slow-gate skips,
  36 subtests;
- definitive Release candidate run 51 at head `bd0ef07` passed all 13 full-suite
  shards and the final aggregate gate;
- CI audited 42 Python test files, 19 Node test files, all 17 candidate-verifier
  tests, composed all-model candidate, and frontend production build;
- broad Python owner passed 591 tests and 111 subtests;
- total workflow elapsed 13m58s with every validation shard capped at 15
  minutes;
- the longest isolated Manager sync/export owner ran 7 passed, 2 skipped in
  12m48s and must not absorb additional work without another split.

Checkpoint 1 is not reopened merely because later work touches its components.
Later checkpoints add regression tests for every preserved behavior.

### Checkpoint 2 — group display-label contract and reviewed migration — complete 2026-08-23

**Authorization gate:** fulfilled in two stages: schema/review generation was
authorized first, then the complete reviewed label set and guarded workbook
migration were explicitly authorized. Neither authorization included the
Checkpoint 5 customer-runtime heading switch.

**Objective:** establish one workbook-owned group label contract and a complete
reviewed migration without changing customer runtime headings.

**Required subpasses:**

1. **2A — baseline and RED contracts**
   - inventory exclusive/rule group families, workbook headers, registry,
     importer/projection, generator, runtime consumers, and tests;
   - add failing registry/schema/projection/generation tests for `display_label`;
   - record exact column placement and compatibility behavior.
2. **2B — additive schema support**
   - update shared registry and every deriving consumer;
   - preserve old workbooks as an explicit migration-required state rather than
     silently inventing labels;
   - expose label and audience/status in connected reads.
3. **2C — review artifact**
   - generate the complete CSV/JSON artifacts from §7.3;
   - verify row count equals the complete existing group inventory;
   - stop for user review and approval.
4. **2D — guarded approved workbook migration**
   - apply only rows marked approved/not-customer-rendered as authorized;
   - create and verify backup;
   - validate package/schema/readback;
   - regenerate affected models and registry;
   - prove no runtime heading switch occurred.

**Likely permitted surfaces after authorization:**

- `scripts/corvette_form_generator/workbook_domain/registry.py`;
- schema validation, importer/generator consumers proven by symbol trace;
- `workbook-manager/backend/app/catalog.py`, `explorer.py`, projection/import
  schema as required;
- the review artifacts named in §7.3;
- focused tests and documentation/handoff;
- canonical workbook and generated outputs only in subpass 2D after label-list
  approval.

**Forbidden in Checkpoint 2:**

- customer runtime heading switch;
- automatic labels;
- group creation or new ID allocation;
- unrelated group membership/rule changes;
- deployment/dealer/media actions.

**Exit gate:** every existing group has an exact review record; every
customer-rendered exclusive group is approved or explicitly blocked; workbook
package/schema and all affected generation/parity gates pass; runtime still uses
its pre-Checkpoint-5 fallback; rollback evidence is complete.

**Mandatory stop:** after 2C and after 2D.

**Completion evidence:**

- the CSV and JSON review companions contain the same stable 224-record
  inventory and approved decisions: 61 customer exclusive groups and 163
  Manager-facing rule groups, with no blank, pending, duplicate, or invented
  hash-derived labels;
- `display_label` sits immediately after `group_id` in all 12 registered group
  sheets; the guarded 224-operation batch matches every saved label on readback;
- rollback points `stingray_master-20260823-015333.xlsx` and
  `stingray_master-20260823-015719.xlsx` hash to the pre-schema and exact
  pre-label-apply identities respectively; the latter matches the bound apply
  batch SHA-256;
- package/schema/options quality pass with zero issues; all six runtime
  contracts and `form-app/data.js` were regenerated, and every non-timestamp
  contract change is a `display_label` under `ruleGroups` or `exclusiveGroups`;
- Manager connected group reads lead with workbook-authored labels and retain
  canonical IDs under technical evidence; a real single-process import/query
  smoke returned `LS6 Engine Covers`, `audience=customer`, and
  `label_status=authored`;
- `form-app/app.js` is unchanged, the `Related options` fallback remains tested,
  and the cache token advanced from 35 to 36 only because the inert additive
  registry payload changed;
- local gates passed: focused label/catalog owners (46), Python metadata (159
  plus 111 subtests), Manager checkpoint (248 passed, 2 skipped, 36 subtests),
  copied-workbook slow Manager gate (70), every Node test file, frontend build,
  Fable validation, and the complete 12-stage all-model candidate lane;
- full-inventory GitHub run 32626231858 passed all 13 planned shards and the
  aggregate `release-candidate` gate at implementation commit `ff28eb5`.

Checkpoint 2 is stopped at its required post-2D boundary. Customer headings
remain owned by separately authorized Checkpoint 5.

### Checkpoint 3 — contextual option/group editing and complete control metadata

**Authorization gate:** explicit authorization of Checkpoint 3. Group label
editing is available only if Checkpoint 2 contract landed; otherwise the field
is read-only/pending.

**Objective:** make option and group changes from their connected context using
registry-driven controls and the existing durable draft lane.

**Required subpasses:**

1. **3A — control inventory and RED matrix**
   - compare every `WRITABLE_COLUMNS` field to current type/enum/ref/control
     metadata;
   - add the exhaustive failure test from §10.8;
   - identify unresolved finite domains and stop only for those decisions.
2. **3B — registry/schema and reference lookup**
   - add explicit control metadata to the shared registry;
   - make `_schema_dict()` fail closed;
   - add bounded human-label reference options;
   - preserve current API members additively.
3. **3C — reusable editor shell**
   - implement accessible desktop drawer/narrow sheet;
   - renderer map has no free-text fallback;
   - local validation, unsaved-close handling, busy/idempotent Save, focus return.
4. **3D — option editor**
   - edit identity/copy, placement/display, and authorized direct fields;
   - relationship panels link to relevant semantic operations rather than raw
     tables;
   - show draft overlay and direct impact immediately after Save.
5. **3E — group/member editor**
   - edit authorized group facts;
   - add/remove/reorder members through existing draft operations;
   - show dependency refusal and deterministic final order;
   - group creation remains blocked unless separately approved.
6. **3F — persistent draft tray/navigation**
   - connected detail accepts active draft overlay;
   - URL/history and model context satisfy §§5–6;
   - draft resume/reload restores the same entity and editor-safe state.

**Likely permitted surfaces:** registry, Manager catalog/schema/routes,
`explorer.py`, `drafts.py` only where the existing operation contract needs
additive metadata, `api.js`, `ConnectedExplorer.jsx`, `RecordForm.jsx` or a new
bounded editor component, `App.jsx`, `styles.css`, and focused tests.

**Forbidden:** canonical workbook write, generated/runtime output change,
apply/rebuild behavior change, new ChangeSet dialect, new UI dependency without
approval, automatic group IDs, and starting section editing.

**Required browser scenarios:** option edit, invalid finite value, invalid/stale
reference, group edit, add/remove/reorder member, dependent refusal, complete
reversion to no effective operation, draft resume after reload, model switch,
deep link, Back/Forward, desktop focus return, and 390x844 no-overflow sheet.

**Exit gate:** every writable field has explicit metadata; constrained fields
cannot render as arbitrary text; connected option/group edits remain draft-only;
overlay/impact and draft tray are correct; all focused, broad Manager, frontend,
accessibility/browser, protected-boundary, and full-suite gates pass.

**Checkpoint 3A/3B completion evidence (2026-08-23):**

- the registry owns exact control metadata for all 220 writable fields across
  all 25 families; the exhaustive owner fails on missing/extra metadata,
  structural-kind/finite-domain disagreement, key mutability, blank-semantics
  disagreement, and unresolved or malformed reference presentation;
- `GET /api/records/{table}/schema` is additively versioned and preserves every
  prior member while requiring normalized `control` metadata; mutation
  validation rejects generated/read-only/immutable control kinds;
- the additive bounded reference-options endpoint derives direct, union, and
  conditional targets from registry/catalog contracts, requires model and
  discriminator context where applicable, returns human labels plus canonical
  secondary IDs, caps pages at 100, and executes exactly one count plus one page
  query; the canonical projection smoke measured two SQL statements and 0.637
  ms for the filtered section lookup;
- the focused owner passed 24 tests and 25 subtests; final catalog/API owners
  passed 56 tests and 25 subtests; the README-owned Manager serial group passed
  223 tests, skipped the two intentional slow-only cases, and passed 61
  subtests; frontend production build, package/schema, catalog/CI planner,
  Fable-contract, and Python compile gates passed;
- the complete 12-stage all-model candidate passed with zero findings,
  unexpected drift, or boundary violations; canonical workbook, retained
  generated contracts, published registry, customer runtime, dealer, media,
  deployment, dependency, durable draft, and apply/rebuild behavior remain
  unchanged.

**Checkpoint 3A/3B defect correction (2026-08-23):** the evidence above
covered only the writable inventory. The read-only `form_sections` projection
carries no `editor_family`, so `_schema_dict()` graded its columns against an
empty writable control set and raised `SchemaIntegrityError` on the first
column, returning 500 from `GET /api/tables` (all structure tables) and
`GET /api/records/form_sections/schema`. The fail-closed owner did not catch it
because its matrix iterated `catalog.WRITABLE_SPECS` rather than
`catalog.TABLE_SPECS`. Corrected by giving read-only families registry-owned
`read_only` control metadata, resolving controls through
`registry.controls_for_family()`, and validating read-only specs against the
read-only contract in §10.2. The matrix now iterates every projected spec and
asserts the read-only projections are present in it. Route-level coverage
asserts `GET /api/tables` returns 200 with `read_only` controls on
`form_sections`.

**Checkpoint 3A/3B review-finding corrections (2026-08-24):** two further
Codex findings on the delivery PR were implemented inside the closed slice.

- *Reference scoping.* A `global` RefSpec applied no model filter, so pickers
  offered other models' rows (`option_availability.variant_id` offered all 32
  variants where 6 are valid). Narrowing now derives from model topology rather
  than the declared scope, and applies only when a model is supplied, so no
  field newly requires one. It is gated on the source row having a model
  identity: `option_availability.variant_id`, `variant_option_overrides.
  variant_id`, `model_interior_scope.interior_id`, and
  `interior_components.interior_id` narrow; `color_overrides.interior_id` does
  not, because that table has no model column. All four narrowed references
  measured zero cross-model rows in the canonical projection, so no stored
  value became unselectable. The finding's stated cause — that the write path
  rejects these values — was incorrect: `_ref_exists()` checks existence only
  for `global` refs, so API and writer already agreed.
- *Section references are deliberately excluded.* The projected
  `form_sections.model_context` is empty for all 48 rows, so the existing
  json_each filter matches zero sections for every model; enabling it would
  empty the section picker. Recorded here as an open projection/contract gap.
- *Blank group labels.* §7.1 requires an approved label on active
  customer-rendered exclusive groups, but blank exited validation unchecked and
  the registry marked the field optional, so an editor operation could clear
  it. `schema_validation` now raises `group_display_label_missing` for a blank
  label on an active `exclusive_groups` row, and
  `registry.ACTIVE_ROW_REQUIRED_COLUMNS` adds `display_label` to
  `required_on_effective_active_row` for that family only — rule-group labels
  stay Manager-facing per §7.1. The requirement applies only once the sheet
  carries the column, and never on a delete. The canonical workbook validates
  clean; `display_label` remains in `optional_columns`, so the §10.2
  blank-semantics invariant is unchanged.

**Checkpoint 3C completion evidence (2026-08-24):**

- one reusable `EditorShell` now presents existing schema-driven record forms as
  a right-side desktop drawer and full-screen narrow sheet with dialog semantics,
  synchronous heading focus, contained Tab/Shift+Tab, safe Escape/backdrop/Close,
  dirty-close confirmation, opener focus return, body-scroll containment, and a
  sticky Save/Cancel footer;
- `RecordForm` now renders normalized registry `control.kind` through one exact
  12-kind renderer map and throws on an unknown kind; the legacy `field_kind`
  branches, 2,000-row generic reference loads, setup-description special case,
  and arbitrary text fallback are removed;
- client validation covers blank, finite/boolean, integer/money bounds, URL, and
  loaded/stale reference states on change/blur and before Save; bounded reference
  lookup uses the 3B endpoint with human labels and canonical IDs; one synchronous
  busy guard plus the existing durable coalescing identity prevents duplicate
  draft intent;
- dependency-free focused coverage passed 8 tests; the catalog owner plus catalog
  contracts passed 35; the README-owned Manager checkpoint passed 301 tests,
  skipped the two intentional slow-only cases, and passed 62 subtests; frontend
  production build, CI planner/finalizer self-tests (5/4), Python compile,
  `git diff --check`, and the complete 12-stage all-model candidate passed with
  zero findings or skipped stages;
- isolated real-browser proof covered desktop drawer geometry and sticky footer,
  required numeric rejection, dirty-close refusal and confirmed discard, heading
  focus, Tab/Shift+Tab containment, Escape, focus/scroll restoration, a bounded
  human-label section reference request, and a literal 390x844 sheet whose shell
  and body had zero local horizontal overflow; no Save ran and draft count stayed
  zero;
- 17 protected baseline hashes stayed identical: canonical workbook, tracked
  generated outputs, published registry, customer runtime, and cache-bearing HTML.
  Dependencies, backend/durable draft semantics, apply/rebuild, dealer, media,
  deployment, and customer runtime remain unchanged.
- PR 42's three P2 editor findings were accepted as contract-preserving corrections:
  initial heading focus now wraps backward Tab to the last editor control, blank
  `never_blank_key` values fail client validation and present as required, and
  Enter in reference search no longer submits the draft form. Focused coverage
  passed 8 tests, the production frontend build passed, and the exact catalog-owned
  Manager serial group passed 251 tests / skipped 2 intentional slow cases / passed
  62 subtests.

**Checkpoint 3D completion evidence (2026-08-25):**

- a mutable option detail now opens a dedicated editor whose direct fields and
  controls derive from existing registry metadata and whose Save uses the
  existing durable draft-operation route; it does not write the workbook or
  rebuild outputs;
- the editor stays open after Save and presents the exact field-level draft
  overlay plus direct-impact counts while the connected detail behind it retains
  availability, groups, rules, pricing, images, and navigation context;
- real-browser proof on Stingray option `5ZU` changed only `option_name`, showed
  the old/new values and impact counts in the post-Save overlay, and showed the
  same field-level operation in Review & Apply; the temporary proof draft was
  cancelled and no Apply/Rebuild ran;
- focused connected-editing tests and the frontend production build passed;
  the README-owned complete Workbook Manager checkpoint passed 306 tests,
  skipped the two intentional slow-only cases, and passed 62 subtests;
  protected workbook/generated/runtime-contract hashes
  matched `origin/main`, and `git diff --check` passed;
- workbook, schema, backend/durable draft contract, generated artifacts,
  published registry, customer runtime, dependencies, deployment, media,
  security, dealer behavior, group/member editing, and persistent draft-tray
  behavior remain unchanged.

**Checkpoint 3D delivery closeout (2026-08-26):** both Codex review findings on
PR 45 were dispositioned as real bugs and fixed on the PR head — the contextual
option editor now seeds its form from the coalesced durable draft operation for
the exact physical row (fetched via `GET /api/drafts/{id}/operations`), so
reopening or "Keep editing" no longer silently reverts previously drafted
fields, and the editable field list derives from the registry table schema
(hardcoded `OPTION_FIELD_ORDER` deleted), so registry-added option columns can
no longer be posted blank. The branch was synced with `main` via
`gh pr update-branch`; the rerun Release candidate suite (plan validation,
changed-workbook-manager-connected-editing, ci-contracts, fable-contracts,
manager-frontend, release-candidate) and the Codex disposition gate all passed
on the merged head; PR 45 merged at `3a8369b` on 2026-08-26. Optional residual
follow-up only: real-browser re-proof of the reopen/Keep-editing path
(behavior covered by Node-run helper tests plus source contracts).

**Checkpoint 3E completion evidence (2026-08-26):**

Review-fix implementation commit: `4b7c06c`.
Review-fix delivery receipt: PR 48 head `4be55b4`; all three Codex threads
resolved; pull-request Release candidate run `32973751490` and full-inventory
workflow-dispatch run `32973812575` passed for that head.

- connected group detail now additively exposes the complete projected group row
  plus backend-owned parent/member table and member key/order/active field
  metadata for both exclusive and rule groups. The shared workbook-domain
  registry owns the group/member family relationship and the Manager catalog
  derives every table/key/reference/order/active binding from those registered
  specs; canonical IDs and source lineage remain in technical evidence;
- mutable group detail opens the existing registry-driven `RecordForm` for
  authorized group facts, and a bounded contextual member editor composes the
  existing schema, human-label reference lookup, dependency inspection, and
  durable update/add/delete operation routes; no second mutation contract or
  frontend relationship map was added;
- member proposals show one deterministic final order, swap only the two
  adjacent order values when possible, support activate/deactivate and
  add/remove, and coalesce complete reversion to no effective operation. Blank
  authored member orders normalize to `10/20/...` rather than colliding at zero.
  Parent removal first requires unsaved member edits to be saved, then evaluates
  the draft-effective member set so staged deletes remove stale projection
  dependencies while staged adds still block removal. Group creation remains
  unavailable because canonical-ID allocation is still unresolved;
- real-browser proof on Stingray `Wheel Center Caps` changed and fully reverted
  the group note to zero draft operations; then staged one add, one removal, and
  one adjacent reorder as four durable operations, showed the exact final
  `10/20/30/40/60` order, refused parent removal with five direct dependents,
  and cancelled the proof draft without Apply/Rebuild. The final backend-
  metadata rebuild reopened the original `10/20/30/40/50` member order with no
  active draft, and a literal 390x844 sheet had zero document, shell, or body
  horizontal overflow. Review-fix browser proof on Z06
  `z06_group_z07_excludes_non_z07_aero` normalized two blank authored orders to
  `10/20`, blocked parent removal while member deletes were unsaved, saved both
  deletes, then reached parent-removal confirmation after the draft-effective
  dependency check; the review proof draft was cancelled with no Apply/Rebuild;
- focused connected-editing coverage passed 23 tests and the frontend production
  build transformed 1,526 modules. The README-owned Manager checkpoint passed
  317 tests, skipped the two intentional slow cases, and passed 62 subtests. The
  complete 12-stage all-model candidate passed with no skipped stages or
  findings, `git diff --check` passed, and all 18 protected workbook,
  `form-output`, published registry, customer runtime, and cache-bearing HTML
  hashes matched `origin/main`;
- workbook/schema data, generated and customer-runtime contracts, publication,
  dependencies, apply/rebuild, dealer, media, deployment, and security behavior
  remain unchanged. The browser proofs intentionally created two durable audit
  drafts and then cancelled both; no canonical or generated write ran.

Mandatory stop: this evidence closes only subpass 3E. Subpass 3F remains
unimplemented and requires explicit sequential authorization; no persistent
draft tray, URL/history, deep-link, or reload-resume work was started.

### Checkpoint 4 — complete form graph and contextual section management

**Authorization gate:** explicit Checkpoint 4 authorization after Checkpoint 3
editor shell/control contract is stable.

**Objective:** replace the incomplete structure join with the complete connected
form graph and make Sections & Layout a first-class workspace.

**Required subpasses:**

1. add RED graph fixtures for every promoted model and known bucket/context type;
2. implement one backend graph assembler and additive endpoint;
3. prove graph parity against freshly generated runtime metadata;
4. add Sections & Layout navigation, filters, connected section detail, and
   deep-link/back behavior;
5. add contextual editing only through the actual writable presentation family;
6. overlay draft graph changes and show parity impact before Review & Apply.

**Likely permitted surfaces:** `explorer.py`, `main.py`, catalog/graph helpers,
`FormStructure.jsx`, a bounded Sections component, `App.jsx`, `api.js`, styles,
and focused graph/browser tests.

**Forbidden:** editing `section_master`/`form_sections`, hand-changing generated
runtime metadata, customer runtime behavior changes, or treating generated
output as source.

**Exit gate:** no false `no sections mapped`; every displayed step/section or
bucket edge has workbook and fresh-runtime evidence; unresolved differences are
explicit; option placement and section edits remain draft-only; all promoted
model parity, browser, and full-suite gates pass.

### Checkpoint 5 — customer group headings and terminology migration

**Authorization gate:** explicit approval of the complete customer label set and
the runtime switch. Every promoted visible exclusive group must satisfy the
Checkpoint 2 contract.

**Objective:** render approved workbook-owned headings in customer forms while
preserving selection behavior and completing user-facing terminology.

**Required subpasses:**

1. add RED generator/runtime contracts for label and separate instruction;
2. update generic generator/runtime consumers—never model-specific hardcodes;
3. regenerate all affected promoted models and registry in isolation;
4. remove generic `Related Options` only after the all-model completeness gate;
5. audit Manager action labels in §12;
6. run responsive/accessibility and customer-flow regressions.

**Forbidden:** changing group membership, selection mode, availability, pricing,
dealer payload/security, deployment, or WordPress media.

**Exit gate:** all promoted model forms use approved labels; selection
instructions remain separate and behavior-identical; no completed-state generic
fallback remains; generated diffs are reviewed; all model switching, selection,
summary/total, download, and safe dealer-modal tests pass without live
submission.

### Checkpoint 6 — Review & Apply presentation recovery

**Authorization gate:** explicit Checkpoint 6 authorization. Reliability
semantics remain owned by the completed workflow specification.

**Objective:** make the complete durable lifecycle understandable from semantic
entity summaries while retaining exact evidence and recovery.

**Required subpasses:**

1. add typed semantic summary/impact response contracts;
2. group review by model/entity and link to connected overlay;
3. preserve exact immutable artifacts under Technical details;
4. complete lifecycle action naming and persistent result states;
5. prove desktop and narrow flows from edit through copied-workbook successful
   Apply and Rebuild, replay, downstream rollback, and manual-recovery boundary.

**Forbidden:** weakening confirmation, identity binding, preview/approval, hash
verification, rollback, single-process serving, or live deployment/dealer/media
behavior.

**Exit gate:** an operator can explain every proposed change, what Save did,
what validation proved, what approval means, what Apply will touch, and the
actual result without reading technical IDs; exact evidence remains accessible;
all lifecycle and full-suite gates pass.

## 17. Validation and evidence strategy

### 17.1 Setup and serving

Use current README commands; at the inspected baseline:

```sh
.venv/bin/python -m pip install -r requirements-test.txt
npm --prefix workbook-manager/frontend ci --include=dev
npm --prefix workbook-manager/frontend run build
./workbook-manager/run.sh
```

Serve through the FastAPI lifespan and single-process path. Do not bypass
lifespan in tests and do not use multiple uvicorn workers.

### 17.2 Test organization for new work

Prefer bounded owners rather than expanding the already large
`tests/test_workbook_manager.py`. Expected checkpoint-focused files are:

- `tests/test_workbook_manager_group_labels.py`;
- `tests/test_workbook_manager_connected_editing.py`;
- `tests/test_workbook_manager_form_graph.py`;
- `tests/test_workbook_manager_relational_performance.py`;
- `tests/test_workbook_manager_review_presentation.py`;
- an existing-harness browser test file when durable browser automation is
  available without a new dependency.

Names are expected ownership boundaries, not permission to create redundant
fixtures. Reuse `workbook_manager_fixtures.py` and the existing verified
projection/candidate owners. New test files are automatically discovered by the
full inventory audit unless deliberately assigned to an explicit heavy shard.

Do not add work to `TestSyncBatch` or `TestComparisonExport` without measuring
and splitting first; their isolated owner already consumes 12m48s of test time.
A validation shard with less than approximately two minutes of total-job
headroom must be split or optimized before merge, not granted a longer timeout.

### 17.3 Inner edit loop

Run the exact test, class, or new focused file while editing. Examples:

```sh
.venv/bin/python -m pytest   tests/test_workbook_manager.py::TestApi::test_connected_option_detail_is_model_scoped_complete_and_read_only -q

.venv/bin/python -m pytest tests/test_workbook_manager_connected_editing.py -q
npm --prefix workbook-manager/frontend run build
```

Do not repeatedly run the complete suite to compensate for missing focused
ownership.

### 17.4 Checkpoint acceptance inventory

At each implementation checkpoint, run the current README-owned Manager
acceptance command in one pytest process:

```sh
.venv/bin/python -m pytest   tests/test_asset_map_sync.py   tests/test_workbook_manager_catalog.py   tests/test_workbook_manager_import_projection.py   tests/test_workbook_manager_fixtures.py   tests/test_workbook_manager_generated_parity.py   tests/test_workbook_manager_api_concurrency.py   tests/test_workbook_manager_drafts.py   tests/test_workbook_manager_changeset_lifecycle.py   tests/test_workbook_manager_apply_rebuild.py   tests/test_workbook_manager.py   tests/test_workbook_manager_group_labels.py   tests/test_workbook_manager_connected_editing.py   tests/test_workbook_manager_form_graph.py   tests/test_workbook_manager_relational_performance.py   tests/test_workbook_manager_review_presentation.py -q
```

Include only files that exist for the authorized checkpoint; update the
README-owned acceptance command when a new permanent owner lands. Do not quote
this specification as command authority after the README changes.

For approved write/apply checkpoints, run the optional copied-workbook slow gate
when relevant:

```sh
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

### 17.5 Whole-product and CI gates

When workbook, generator, generated contract, publication, validation
infrastructure, or multiple relational surfaces change, run the composed
all-model candidate:

```sh
.venv/bin/python scripts/verify_workbook_candidate.py   --workbook stingray_master.xlsx   --changed-model '*'
```

Validation-planning changes also run:

```sh
python scripts/test_finalize_ci_validation_plan.py
python scripts/test_split_ci_validation_plan.py
```

Before checkpoint closeout:

```sh
git diff --check
```

If `fable5loop/STATE.md` or `fable5loop/STATE-archive.md` change:

```sh
.venv/bin/python scripts/validate_state_handoff.py
```

The pull request must receive one successful full-inventory Release candidate
run for checkpoint closeout. The run must prove every planned shard and the
aggregate gate, not only the changed-surface slice. Ordinary subsequent PR
commits may remain changed-surface planned unless the workflow forces full or a
manual full-suite dispatch is required for final evidence.

### 17.6 Protected-boundary evidence

Read-only checkpoints capture pre/post SHA-256 evidence or an equivalent tested
manifest for:

- canonical workbook;
- tracked `form-output/` artifacts;
- `form-app/data.js`;
- customer runtime files and cache-bearing HTML;
- durable Manager state when the checkpoint is not supposed to write it.

The existing verified fixture/hash helpers are preferred over a new ad hoc
manifest. The final diff must also show no unintended workbook/generated/runtime
changes.

Approved write checkpoints record:

- pre-write workbook identity and verified backup;
- exact reviewed row operations;
- package/schema and semantic readback;
- affected-model generation candidate hashes;
- published registry/cache-version result;
- rollback set and restoration proof;
- post-write re-import/projection state.

### 17.7 Required API/query tests

Coverage includes:

- response schema version and projection fingerprint;
- identity/model scoping and no cross-model leakage;
- complete relationship sets with lineage;
- search ranking, filters, stable order, limits, and no N+1 query regression;
- query budgets in §6.10;
- diagnostics definition/result contract and pagination;
- draft overlay for modify/add/delete/conflict;
- bounded human-label reference lookup;
- capability and blocked-reason accuracy;
- error envelope and safe next action;
- no write from read-only endpoints.

### 17.8 Required browser and accessibility scenarios

Use the existing browser harness when available. Adding Playwright, Cypress, or
another dependency requires approval. Evidence covers:

- readiness, stale reload, backend unavailable, and recovery states;
- deep-link load, Back/Forward, return-to-origin focus, and model switch;
- typed search and each connected entity type;
- option/group/section editor visibility and focus;
- finite/reference/numeric invalid input blocked before Save;
- draft overlay, tray, resume, reversion, and conflict;
- member add/remove/reorder and dependency refusal;
- Review & Apply semantic summaries and connected links;
- desktop plus 390x844 layout with no horizontal overflow;
- keyboard reachability, focus visibility/trap/return, semantic headings and
  regions, non-color state cues, and no icon-only primary/destructive action;
- no unexplained expected 404/409/503 console errors;
- no live dealer submission, media mutation, deployment, or cache purge.

### 17.9 Acceptance scenario matrix

| ID | Checkpoint | Scenario | Required result |
|---|---:|---|---|
| NAV-01 | 3 | Open option from search, then group, then browser Back twice | Exact prior entity/result/query/model/focus restored. |
| NAV-02 | 3 | Reload direct option/group URL | Same entity opens after readiness; no raw-table fallback. |
| NAV-03 | 3 | Switch model during in-flight search | Prior response cannot overwrite new model. |
| EDIT-01 | 3 | Edit option finite/reference fields | Valid draft operation, immediate overlay, workbook unchanged. |
| EDIT-02 | 3 | Existing invalid legacy value | Explicit invalid state; not added as valid choice. |
| GROUP-01 | 3 | Add/remove/reorder member | Deterministic operations/order and connected impact. |
| GROUP-02 | 3 | Remove parent with dependents | Direct warning; incomplete graph fails preview. |
| DRAFT-01 | 3 | Reload with nonterminal draft | Same draft and connected overlay resume. |
| DRAFT-02 | 3 | Projection changes after draft | Overlay conflicts and blocks ordinary Save/apply. |
| GRAPH-01 | 4 | Compare every promoted model graph to fresh runtime | No unexplained missing/extra step-section edges. |
| GRAPH-02 | 4 | Standard-equipment bucket | Presented as bucket, never false unmapped step. |
| LABEL-01 | 2 | Generate review artifact | One stable record per existing group, no auto-approved label. |
| LABEL-02 | 5 | Render approved exclusive group | Workbook label heading plus separate instruction. |
| APPLY-01 | 6 | Copied-workbook successful apply | Exact artifacts applied, outputs rebuilt, projection stale until reload. |
| APPLY-02 | 6 | Downstream generation failure | Workbook/outputs restored and hash-proven or manual recovery only. |
| A11Y-01 | 3–6 | Keyboard-only drawer/sheet flow | Focus enters, stays, error focuses, closes, and returns correctly. |

### 17.10 Reporting

Report every check actually run with command and result. List every relevant gate
not run and why. Never claim full inventory, browser proof, workbook safety, or
runtime parity from an adjacent test or remembered prior run.

## 18. Non-goals

- Rebuilding the Manager as a generic spreadsheet editor.
- Making SQLite or a draft overlay canonical.
- Replacing the reliable workflow, ChangeSet, preview, approval, apply, rollback,
  or recovery contracts.
- Inventing availability, pricing, defaults, relationships, membership, labels,
  or other business data.
- Automatically generating customer-facing labels from IDs, notes, or members.
- Treating same RPO across models as canonical entity equivalence.
- Hand-editing generated artifacts or customer runtime as a source fix.
- Hiding advanced traceability/recovery evidence merely to simplify normal UI.
- Adding a graph-visualization library, router, modal library, form library, or
  other dependency without separate approval; connected relational lists and
  native History API are sufficient unless evidence proves otherwise.
- Changing WordPress media, deployment, production cache, dealer submission,
  customer identity, or security behavior.
- Restoring arbitrary row comparison or purposeless selection.
- Starting a later checkpoint to close an earlier checkpoint.

## 19. Approval gates, open decisions, and current next action

### 19.1 Current authorization state

Checkpoints 1 and 2 are complete. Checkpoint 3A/3B's bounded
registry/schema/reference slice, Checkpoint 3C's reusable shell, Checkpoint
3D's direct option editor, and Checkpoint 3E's contextual group/member editor
are complete and stopped. Checkpoint 3F and Checkpoints 4–6 remain unauthorized.
The next implementation agent must receive an explicit checkpoint instruction
and must not treat either the completed label migration or control metadata as
authorization for customer headings.

### 19.2 Decision matrix

| Decision | Required before | Current state |
|---|---|---|
| Add `display_label` to exclusive/rule group workbook families | Checkpoint 2A/2B | Complete: registry, validation, projection, generator, and all 12 workbook sheets agree. |
| Exact column placement and compatibility behavior | Checkpoint 2B | Complete: immediately after `group_id`; pre-migration workbooks report an explicit pending-migration state. |
| Complete actual group label/classification list | Checkpoint 2D | Complete: 224/224 reviewed labels approved and written; CSV/JSON companions and workbook readback agree. |
| Switch customer headings to workbook labels | Checkpoint 5 | Label prerequisite is complete; runtime switch still requires explicit Checkpoint 5 approval. |
| Add complete control metadata and bounded reference lookup | Checkpoint 3A/3B | Complete locally: 25 families / 220 fields have exact coverage; schema/reference APIs are additive and fail closed. Delivery CI is recorded with the PR. |
| Reusable accessible registry-control editor shell | Checkpoint 3C | Complete locally: drawer/sheet, no-fallback renderer map, validation, dirty-close, busy Save, focus, and responsive browser proof are green; delivery CI is recorded with the PR. |
| Render and save a contextual direct option editor | Checkpoint 3D | Complete and merged: registry-driven direct fields, durable draft Save, field overlay, impact summary, connected detail, focused/build/Manager gates, and browser proof are green; both Codex review-bug fixes landed on the PR head, post-sync CI passed, and PR 45 merged at `3a8369b`. |
| Render and save contextual group/member editors | Checkpoint 3E | Complete locally: registry-driven group facts, durable member add/remove/reorder/active operations, deterministic final order, direct dependency refusal, reversion, focused/build/Manager/all-model gates, protected hashes, and browser proof are green. Delivery CI is recorded with the PR. |
| New group canonical-ID allocation strategy | Any Add Group feature | Unresolved; Add Group remains blocked. |
| Any new frontend/backend dependency | Before dependency change | Not approved. |
| Breaking/removing existing Manager API members | Before API break | Not approved; changes must be additive. |
| New deployment, media, security, or dealer behavior | Before change | Not approved and outside this recovery. |

### 19.3 Evidence-driven finite domains

Checkpoint 3 may encode accepted vocabularies and references only when current
workbook rows, registry, generator parsing, runtime consumers, and validators
establish the complete domain. One observed value does not prove a vocabulary.
When evidence is incomplete, record family/field/current values/consumers and
stop for the narrow product decision instead of guessing or leaving accidental
free text.

Checkpoint 3A resolved the complete writable inventory as 25 registered
families / 220 fields, with exact control coverage and no fallback: boolean 30,
finite 18, integer 15, long text 31, money 4, reference 27, short text 85,
structured text 8, and URL 2. The accepted additional finite domains are:

| Family / field | Registered values | Evidence and consumers |
|---|---|---|
| `interior_components.component_type` | `seat`, `suede`, `stitching`, `r6x`, `two_tone` | All 1,044 authored component rows plus `interiors.py` / `runtime_metadata.py` assembly. |
| `context_section_master_meta.selection_mode` | `single_select_req`, `single_select_opt`, `multi_select_opt`, `display_only` | Exact `SELECTION_MODE_LABELS` generator vocabulary in `model_configs.py`; authored rows use a member of that set. |
| `section_presentation_meta.standard_equipment_group_type` | blank or `trim_equipment` | Authored rows contain only this domain and `form-app/app.js` performs the exact `trim_equipment` comparison. |

The following candidate domains remain deliberately non-finite. Checkpoint 3B
records them as explicit text/structured-text controls rather than inferring a
dropdown; a later UI may not convert them to a finite/reference selector until
the named decision is resolved:

| Family / field | Current authored evidence | Unresolved decision / consumer |
|---|---|---|
| rule/default/price families: `body_style_scope`, `trim_level_scope`, `variant_scope` | `*`, coupe/convertible, LT/LZ values with mixed case; current `variant_scope` rows use only `*` | Scope grammar and case normalization belong to the existing rule/price parsers; one observed token set does not prove the full grammar. |
| `asset_map.target_type` | `context_choice`, `model`, `option` | Only `option` currently has a conditional registry reference. Defining identity/reference sources for context choices and models is a separate registry decision. |
| `variant_master.body_style`, `variant_master.trim_level`, `model_interior_scope.trim_level` | body values `*`, coupe, convertible; trim values span 1LT–3LT and 1LZ–3LZ with upper/lower-case rows | Whether these become model-variant references or a normalized vocabulary would change workbook authoring behavior and is not proven by current rows alone. |
| `interior_components.price_ref_type`, `interior_components.price_trim_scope` | types include both `two_tone` and `twotone`; scopes include LT/LZ and `_R6X` forms | Existing component-pricing consumers accept aliases/special scopes; normalization or retirement is a business-data migration, not a control inference. |
| context metadata: `choice_mode`, `context_type`, `standard_behavior` | `single`; `body_style`/`trim_level`; three standard-behavior values | Current workbook rows are examples, not a complete registry/generator vocabulary. |
| provenance/presentation text: `source`, `grouping_source`, `display_behavior` where no family enum exists | source labels and audit paths are intentionally open-ended; some presentation families currently author no value | These are provenance or family-specific presentation fields, so values observed in a different family do not establish a shared finite domain. |

This inventory stops only the unresolved conversions above. It does not block
the registry/schema metadata slice because those controls are now deliberate,
exhaustively tested text controls rather than accidental frontend defaults.

### 19.4 Current next action

Remain stopped after Checkpoint 3E. The next sequential implementation action
is an explicit decision on Checkpoint 3F's persistent draft tray/navigation.
Do not begin 3F automatically, do not skip ahead to later checkpoints, and do
not begin the non-sequential Checkpoint 5 customer-runtime heading switch merely
because its label prerequisite is complete.

## 20. Coding-agent checkpoint execution protocol

The checkpoint execution protocol, working definition of done, preflight,
reporting duties, and handoff receipt are owned by `AGENTS.md` (§4, §10–12) and
the reliable workflow specification. This section adds only what is
checkpoint-specific:

1. **Start:** state the authorized checkpoint and quote its exit gate; run the
   AGENTS-aligned preflight (`git status --short`, branch, HEAD, PR state) and
   re-resolve current repository/workbook state before relying on any recorded
   baseline; write the concise definition of done from §1.3; capture protected
   baseline evidence (§17.6).
2. **Implement:** narrow RED test first; minimum source-of-truth change; focused
   test green before broader runs; backend/registry contract before frontend
   inference; UI response stays in initiating context with verified focus; no
   unrelated cleanup.
3. **Verify:** run the gates named by §16 and §17 for the changed surface;
   report every command and result plus every relevant gate not run and why
   (§17.10).
4. **Close out:** inspect `git status` and final diff for temporary/unrelated
   files; update this specification only for requirement status/evidence/
   blocker changes; rewrite the fixed `fable5loop/STATE.md` handoff per
   `AGENTS.md` §9; record delivery (branch, commit, PR); stop without starting
   the next checkpoint.

### 20.1 Copy-ready coding-agent task template

```text
Execute Checkpoint <N / subpass> of
`docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md`.

Authority and scope:
- Read `AGENTS.md`, the reliable workflow specification, the Workbook Manager
  README, this specification, and the current operational handoff before editing.
- This task authorizes only <checkpoint/subpass>.
- Do not begin any later checkpoint.
- Preserve workbook/generated/runtime/dealer/media/deployment boundaries except
  where this subpass explicitly authorizes them.

Required preflight:
- Show `git status --short`, branch, HEAD, and material drift from the spec
  baseline.
- Identify current source/test owners and unrelated user work.
- State a concise definition of done, RED tests, protected surfaces, validation,
  rollback, and stop conditions.

Implementation:
- Follow the ordered subpasses and file permissions in §16.
- Backend/registry owns relation and control semantics; React must not invent
  joins, allowed values, or business rules.
- Use the existing durable draft and immutable ChangeSet lifecycle.
- Keep changes minimal and checkpoint-local.

Acceptance:
- Run the focused tests, frontend build, required browser scenarios, broader
  Manager inventory, applicable all-model/workbook gates, `git diff --check`,
  and a full-inventory Release candidate run.
- Report exact commands/results, relevant gates not run, protected behavior,
  residual risk, branch/commit/PR, and the next gated action.
- Stop after checkpoint closeout.
```

### 20.2 Checkpoint receipt template

```markdown
### Checkpoint receipt

- Authorization:
- Baseline branch / HEAD / PR:
- Current checkpoint and exit gate:
- Diagnosis and evidence:
- Files changed:
- Workbook rows/families changed:
- Generated artifacts changed:
- User-visible behavior changed:
- Protected behavior confirmed unchanged:
- Companion files inspected-no-change:
- Focused tests:
- Frontend build:
- Browser/accessibility evidence:
- Broader Manager suite:
- Workbook/all-model/parity gates:
- CI inventory/run:
- Gates not run and why:
- Rollback/restoration evidence:
- Residual risk:
- Specification/STATE update:
- Delivery branch / commit / PR:
- Exact next gated action:
```

## 21. Revision record

2026-08-24 Checkpoint 3C closure:

- replaced the inline generic form with the reusable accessible desktop
  drawer/narrow sheet and explicit registry-control renderer map;
- added client validation, bounded human-label references, dirty-close handling,
  synchronous focus containment/return, and one-in-flight draft Save behavior;
- recorded focused, Manager checkpoint, frontend build, browser/responsive,
  all-model candidate, planner, protected-hash, and diff evidence;
- preserved workbook/generated/runtime/dealer/media/deployment and durable
  apply/rebuild boundaries and stopped before Checkpoint 3D.

2026-08-23 Checkpoint 2 closure:

- recorded the two-stage authorization, reviewed 224-label inventory, guarded
  12-sheet migration, rollback hashes, regenerated six-model artifacts, and
  Manager authored-label presentation;
- reconciled the CSV/JSON review companions and pinned their validation domain
  to the workbook registry rather than a review-script-local taxonomy;
- recorded local package/schema/generation/Manager/Node/frontend evidence and
  full-inventory Release candidate run 32626231858;
- preserved the customer runtime heading fallback and stopped before
  Checkpoints 3–6.

2026-08-22 tightening revision:

- fixed the task template to reference this specification, not the superseded
  8-15 file;
- replaced the invented §6.10 SQL-statement caps and 500 ms target with a
  measured-baseline-plus-regression-ceiling contract;
- removed pixel-level drawer/viewport constants from §9.4 and pinned label
  length bounds to the Checkpoint 2B registry validation;
- collapsed §§20–22 into one checkpoint-specific protocol that defers general
  conduct, preflight, reporting, and receipt ownership to `AGENTS.md` and the
  reliable workflow specification.

2026-08-21 hardening revision:

- reconciled status with completed Checkpoint 1 and definitive PR 37 full-suite
  run 51;
- removed the obsolete 25-minute single-job narrative and pinned the 15-minute
  bounded-shard contract;
- added authority, preflight, definition-of-done, stop-condition, and handoff
  protocols;
- specified relational identities, edge vocabulary, additive read-model
  envelope, draft overlay, impact analysis, deep links, search ranking,
  diagnostics, query budgets, and bounded reference lookup;
- specified exact group-label review artifacts and approval stops;
- specified complete form-graph assembly and Sections & Layout ownership;
- replaced accidental free-text behavior with an executable registry control
  metadata contract;
- expanded Checkpoints 2–6 into independently runnable subpasses with permitted
  and forbidden surfaces, tests, browser scenarios, and exit gates;
- added CI ownership/headroom requirements so new validation cannot silently
  escape or overrun the full suite.
