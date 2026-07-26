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

No semantic difference. The workbook builder adds three draft-only provenance fields
(`source_active`, `preview_included`, `model`), all stripped from the runtime contract by
`live_contract_data()`.

### Axis 5 — rule assembly

Beyond the 31 dropped rules, the 114 shared rules differ on one column: `source_selection_mode`,
populated by production on 19 rules and blank in the workbook builder. Open item for stage 2.

### Axis 6 — price validation

**No difference.** 49 price rules, identical identities and fields.

### Validation rows

Production emits 3 rows; the workbook builder emits 7 — a superset covering interiors, price rules,
and color overrides, plus the `*_draft_status` warning that `live_contract_data()` strips. Richer, not
divergent.

## Decisions needed before stage 2

1. **`display_behavior` on the 1,385 choices with no value** — emit `""` (workbook builder) or omit
   the key (production)? Behaviorally identical; it changes the published artifact and the
   characterization test's assertion.
2. **Dropping the 31 rules, 8 colorOverrides, and 18 sections from Stingray's published contract.**
   Measured inert, but it is a visible change to `form-app/data.js` and should be an explicit call
   rather than a side effect of convergence.

## Explicitly out of scope for stage 1

Any source change, including the `contract.label_for()` interior fix folded into this receipt. Any
workbook write. Any artifact publication. Requirements 8 and 10.
