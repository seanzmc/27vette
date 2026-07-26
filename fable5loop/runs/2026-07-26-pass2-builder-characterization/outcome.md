# Outcome rubric — Pass 2 receipt C, stage 1: builder difference ledger

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §4 Pass 2,
required behavior **3**: "Before that absorption, characterize and resolve the two builders'
differences in standard-equipment deduplication, hidden/display behavior, variant overrides,
invalid-reference filtering, rule assembly, and price validation. Prefer expressing each difference
in workbook data over encoding it in generic code. Do not hide differences behind count-only
assertions."

Stage 1 is **read-only**. No source change, no workbook write, no artifact publication. Its only
output is the ledger below plus this receipt.

Requirement 3 orders this before requirement 2's absorption, and it is the first receipt in this pass
whose proof is *not* byte-identity: merging two builders that genuinely differ must change Stingray's
output. Every difference therefore has to be enumerated and dispositioned before any code moves.

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Both builders run against the same frozen workbook snapshot in an isolated root | PASS |
| 2 | Every collection is diffed on a **stable semantic identity**, never a positional id | PASS — `override_id` proved positional and was replaced with `(interior_id, option_id, adds_rpo, rule_type)` |
| 3 | Every one of requirement 3's six axes is addressed with a measurement, not a reading | PASS — see the ledger |
| 4 | Each difference is traced to a workbook cause, not left as "the builders differ" | PASS — all six trace to entity activeness or model scope |
| 5 | Each difference carries a disposition and a customer-visibility verdict | PASS |
| 6 | Differences that change customer-visible output are surfaced for the user, not decided silently | PASS — two are flagged in §Decisions |
| 7 | No source change, workbook write, or artifact publication in stage 1 | PASS |

## Method

`build_production_source_data(config)` and `build_form_data_draft(config)` were run against the same
`ModelConfig` bound to a temporary root, and their payloads diffed per collection on a stable key.
Stingray is the only model with both code paths, so it is the entire characterization surface.

## The ledger

### Headline

| collection | production | workbook | verdict |
|---|---|---|---|
| variants, steps, contextChoices, choices, standardEquipment, ruleGroups, exclusiveGroups, priceRules, interiors, defaultSelectionRules | — | — | **identical counts, identical identities** |
| sections | 50 | 32 | production emits 18 sections with zero Stingray rows |
| rules | 145 | 114 | production emits 31 rules referencing `active=False` options |
| colorOverrides | 245 | 237 | production emits 8 overrides for interiors outside Stingray's scope |

**Every difference points the same way: the production builder ships rows referencing entities that
are not in Stingray's own scope.** The workbook builder filters them. Nothing is lost by converging;
dead payload is dropped.

### Axis 1 — invalid-reference filtering (the substantive difference)

**31 rules.** All 31 are real `rule_mapping` rows with real `rule_id`s — not derived, not synthesized;
`runtime_authored_rule()` returns `True` for all of them. No workbook column distinguishes them
(`active`, `runtime_action`, `review_status`, `rule_scope`, `source_sheet`, `notes` are blank for both
the dropped and the kept set). The discriminator is their **endpoints**:

| endpoint resolvability | count |
|---|---|
| source resolvable, target not | 10 |
| target resolvable, source not | 17 |
| neither resolvable | 4 |

Every one of the 31 has at least one unresolvable endpoint. Four option ids account for all of them:

| option | RPO | name | `stingray_options.active` |
|---|---|---|---|
| `opt_5vm_001` | 5VM | Visible Carbon Fiber Ground Effects | **False** |
| `opt_5w8_001` | 5W8 | Carbon Flash Metallic Carbon Fiber Ground Effects | **False** |
| `opt_5zw_001` | 5ZW | Visible Carbon Fiber Two-Stanchion Spoiler | **False** |
| `opt_ryq_001` | RYQ | Visible Carbon Fiber Door Intake Trim | **False** |

So: **deactivating an option in the workbook does not currently remove its rules from Stingray.**
That is a defect in the production builder that convergence fixes.

**8 colorOverrides.** All reference `3LT_AE4_EL9` and `3LT_AH2_EL9` — interiors with **no active
`model_interior_scope` row for Stingray**. Their `option_id`s are active; the interiors are not
Stingray's.

**18 sections.** All have zero Stingray choices and zero Stingray standard equipment. Several belong
to other models outright: `sec_gsce_001`/`sec_gsha_001` (Grand Sport), `sec_lzint_001..003` and
`sec_z06_pkg_001`/`sec_z06_cf_whee_001` (Z06), `sec_perf_z52_001`. Production emits every
`section_master` row; the workbook builder emits only sections a model actually populates.

**Customer impact: none.** All three groups are inert in the browser. A rule whose source is not in
`choices` can never be selected, so `selectedIds.has(rule.source_id)` is never true; a rule whose
target is not in `choices` has no card to disable. An empty section renders nothing. This is dead
payload, not behavior.

### Axis 2 — hidden/display behavior

Not a semantic difference. Identical values on the 31 choices that have one
(`default_selected` 15, `display_only` 10, `auto_only` 6). On the other 1,385, production **omits the
key** and the workbook builder emits `""`. Serialization only.

This resolves the long-standing `test_shared_assembler_preserves_stingray_runtime_drift_surfaces`
failure, which asserts `"display_behavior" not in choice` for `opt_uqt_002`. It is an
absent-vs-empty-string assertion, not a behavioral one. **Needs a decision — see §Decisions.**

### Axis 3 — standard-equipment deduplication

**No difference.** 467 rows, identical identities, identical fields, in both builders. The
`sec_stan_002` ranking in `production.standard_equipment_preference()` produces the same result the
workbook builder reaches without it, on current data.

Related but separate: `standard_equipment_group_type` differs on **62 choices** (production
`trim_equipment`, workbook `""`), while the `standardEquipment` collection itself is identical. Open
item for stage 2.

### Axis 4 — variant overrides

No semantic difference. The workbook builder adds three provenance fields (`source_active`,
`preview_included`, `model`).

**Correction (verifier, 2026-07-26):** this section originally claimed they are "all stripped from
the runtime contract by `live_contract_data()`." That is **false**. `DRAFT_ONLY_LIVE_CONTRACT_FIELDS`
(`runtime_contract.py:10-22`) does not contain them and they ship in all six published contracts.
They were already shipping for the other five models before this pass; convergence extends them to
Stingray. See the stage-2 undisclosed-delta table.

### Axis 5 — rule assembly

Beyond the 31 dropped rules, the 114 shared rules differ on one column: `source_selection_mode`,
populated by production on 19 rules and blank in the workbook builder. Open item for stage 2.

### Axis 6 — price validation

**No difference.** 49 price rules, identical identities and fields.

### Validation rows

Production emits 3 rows; the workbook builder emits 7 — a superset covering interiors, price rules,
and color overrides, plus the `*_draft_status` warning that `live_contract_data()` strips. Richer, not
divergent.

## Decisions taken 2026-07-26

1. **`display_behavior`: omit the key when there is no value.** User's instruction was "whatever is
   the least change" — omitting matches what ships today, so the 1,385 choices are untouched and only
   the 31 with a real value carry the field. The characterization test's
   `"display_behavior" not in choice` assertion stays valid as written.
2. **Drop the 31 rules, 8 colorOverrides, and 18 sections** from Stingray's published contract.
   Approved. All measured inert in the browser.

## Explicitly out of scope for stage 1

Any source change, including the `contract.label_for()` interior fix folded into this receipt. Any
workbook write. Any artifact publication. Requirements 8 and 10.


---

# Stage 2 — convergence

Spec requirements **2** (one builder, no module globals), **3** (differences resolved), plus the
`contract.label_for()` interior defect folded in at the user's direction.

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | `assemble_model_source()` contains no model-keyed source fork | PASS |
| 2 | `production.py` retains no mutable module globals and no workbook access on any surviving path | PASS — 731 lines to 62; compatibility export only |
| 3 | Every published difference matches the stage-1 ledger exactly; nothing unexplained | **FAIL, corrected** — the verifier found eight deltas this receipt did not list. All eight are browser-inert and none is a code defect, but completeness was this criterion's whole burden. Listed in full below. |
| 4 | Decisions 1 and 2 implemented as approved | PASS |
| 5 | `label_for()` names interiors as the browser does, for every model | PASS — 71 composed reasons corrected across five models |
| 6 | Contract invariants hold for all six models, expressed as requirement-derived tests | PASS — 31 assertions |
| 7 | Every validation check the retired builder had is ported or explicitly recorded | PASS — 1 ported, 4 recorded (one now structurally impossible) |
| 8 | Workbook opens per six-model run drop | PASS — 13 to 7 |
| 9 | No new test failure vs HEAD | PASS — 5 pre-existing Python, all 16 node gates at or above baseline |
| 10 | No workbook write, artifact publication, or registry change | PASS |

## Known gap in this stage

The new builder **filters** dangling rules where the retired one **flagged** them. That is the
approved decision 2 for payload, but it also silently removes a reporting signal. Recorded rather
than resolved.


## Undisclosed published deltas — found by the verifier, all browser-inert

The receipt claimed the delta matched the stage-1 ledger exactly. It did not. Every one below was
independently confirmed inert (`app.js` reference count in the last column), and none changes
behavior, but they belong in the record:

| # | Delta | Rows | `app.js` refs |
|---|---|---|---|
| 1 | `interiors.requires_z25` **added** to Stingray | 130 | 0 |
| 2 | `variants` gain `source_active`, `preview_included`, `model` | 6 | 0 |
| 3 | `sections.source_section_name` added | 30 | 0 |
| 4 | `rules.source_selection_mode` **lost** | 19 | 0 |
| 5 | `steps.section_ids` changed | 5 | 0 |
| 6 | `runtimeRuleExceptions` top-level key removed (was `[]`) | — | guarded by `Array.isArray` |
| 7 | `dataset.source_sheet` added | — | 0 |
| 8 | Stingray swap manifest: `candidate_count` 9→1, `not_emitted` 6→0, `shadowed` 3→1 | — | inspection artifact only |

Item 4 is the worst miss: stage 1 explicitly flagged `source_selection_mode` as an "open item for
stage 2" and then it never reached the stage-2 delta table.

**What these actually are.** Measured after the fact: all eight make Stingray match the field set the
other five models already shipped. The only remaining per-model difference in `interiors`, `variants`,
`sections`, `rules` and `choices` is the model-scoped `active_for_{model_key}` flag. So this is
Stingray joining the shared shape — the intended outcome of convergence — but nothing pinned it.
`test_every_model_ships_the_same_contract_shape` now does.

## A deleted assertion the receipt did not account for

The retired `test_source_assembly_characterization.py` contained
`assert all("requires_z25" not in row for row in runtime["interiors"])`. It **passed** at baseline:
the retired `production.py` popped the field with the comment *"Keep the existing Stingray runtime
contract byte-for-byte compatible."* The new builder emits it on all 130 rows, so the assertion would
now fail — and it was deleted with the rest of the file and not replaced.

The receipt attributed that test's long-standing failure solely to the `display_behavior`
absent-vs-empty assertion. True but incomplete. Decision: **accept the field**, because it aligns
Stingray with the other five rather than diverging it, and pin the shared shape with a new test
instead of re-adding a Stingray-only absence assertion.

## Corrections to the recorded counts

- Baseline at `993d920` is **6 failed**, not the "5 failed, 467 passed" recorded. After: 5 failed,
  495 passed — one pre-existing failure fixed, none introduced. The conclusion held; the number did not.
- `missing_{key}_{price_rule_id}` was never listed among the retired builder's checks, but it **is**
  covered — by `price_rule_unknown_condition_` / `price_rule_unknown_target_` (`inspection.py:332,342`),
  plus new duplicate-id and invalid-type checks.
- `redundant_{rule_id}` was recorded as "not ported". The **payload suppression survives** in the
  shared `rules.py:163,201-202`; only the info-severity reporting row is gone.

## The verifier's stronger proof of inertness

My argument for the 31 dropped rules ("a source not in `choices` can never be selected") was
incomplete. `app.js:1116-1120` also disables a choice when it is the **source** of a `requires` rule
whose target is unselected, and `computeAutoAdded` (1059-1062) auto-adds via an `includes` rule with
a live source. A dropped `requires` rule with a resolvable, active source would therefore have
**unblocked a previously-disabled option** — a real customer-visible change.

The verifier enumerated all 31 against the baseline contract and found that class **empty**: all 8
`requires` and the single `includes` have unresolvable sources, and the 10 `excludes` with live
sources all have unresolvable targets. The conclusion stands; my route to it was weaker than it
should have been.
