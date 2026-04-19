# Critical Review: Corvette Ingest / Build Skill Contract

This report merges the original audit with the supplemental review into one file-backed assessment of what is still missing or underspecified in [ingestSkill.md](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:1) and [buildSkill.md](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:1).

The high-level architecture is strong: ingest is trying to preserve source facts, and build is trying to interpret those facts into a runtime order flow. The current risks are mostly contract risks. Several source shapes are named but not defined, several ingest outputs do not close cleanly into build inputs, and several build-sheet columns are mandatory without a deterministic authoring procedure.

## Executive Summary

The biggest blockers are:

1. Ingest does not fully define how to read several source types or how to normalize some core fields.
2. The Color and Trim outputs do not form a closed handoff contract into build.
3. Build does not define a repeatable algorithm for turning ingest rows into `<Variant>` rows.
4. Exception handling, model-family coverage, and rerun/year boundaries are still underspecified across the two skills.

## Findings

### Critical

1. **Availability-code mapping is incomplete.**

Evidence: [corvette-ingest/ingestSkill.md:24](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:24), [corvette-ingest/ingestSkill.md:222](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:222), [corvette-ingest/ingestSkill.md:223](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:223), [corvette-ingest/ingestSkill.md:359](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:359)

The legend announces `S`, `A`, `--`, `D`, `■`, `□`, and `*`, but the skill never gives a full raw-code-to-label table. The schema references `S`, `A`, `A/D`, `--`, and an "Included in Equipment Group" label, but it never explicitly says which raw symbol maps to which label, or how `D`, `■`, `□`, and `*` should be stored.

Impact: `Availability Long` can become inconsistent across runs, and some matrix cells may get pushed into `Ingest Exceptions` simply because the legend contract is unfinished.

Recommendation: add one explicit mapping table for every legend symbol, including whether the symbol is a standalone availability state, a modifier to another state, or a footnote-like flag that should be preserved separately.

2. **Standard Equipment and Equipment Groups are named inputs, but their extraction paths are not specified.**

Evidence: [corvette-ingest/ingestSkill.md:3](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:3), [corvette-ingest/ingestSkill.md:170](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:170), [corvette-ingest/ingestSkill.md:190](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:190), [corvette-ingest/ingestSkill.md:208](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:208), [corvette-ingest/ingestSkill.md:285](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:285)

The front matter says ingest handles `Standard Equipment 1-4` and `Equipment Groups 1-4`, and the schema depends on those sheets for both identity and standard/included semantics. But the body never defines what those sheets look like or how to extract them if they are not ordinary matrix tabs.

Impact: standard-equipment confirmation, trim inclusion, and bundle membership are all too important to leave to guesswork, and the later cross-check against Standard Equipment is not implementable if the sheet shape itself is undefined.

Recommendation: add dedicated extraction rules for Standard Equipment and Equipment Groups, including expected sheet shape, how rows map into `Availability Long`, and how bundle contents or trim inheritance should be recorded.

3. **The price-schedule input contract is incomplete, including `price_mode` derivation.**

Evidence: [corvette-ingest/ingestSkill.md:172](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:172), [corvette-ingest/ingestSkill.md:231](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:231), [corvette-ingest/ingestSkill.md:241](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:241), [corvette-ingest/ingestSkill.md:251](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:251), [corvette-ingest/ingestSkill.md:319](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:319)

The `Pricing Long` schema is clear, but the skill never fully defines the input shape it is extracted from, how context prose is attached to a price row, or how `price_mode` is derived. The enum exists, but there is no rule for `paid` vs. `included_standard` vs. `no_charge` vs. `credit` vs. `surcharge`.

Impact: pricing output will vary by operator, and build cannot rely on consistent semantics for standard/no-charge/credit behavior.

Recommendation: define the accepted price-schedule source formats, the row/column map, the rule for capturing `context_note_raw`, and a precise `price_mode` translation table.

4. **Option Catalog classification and note provenance are underspecified.**

Evidence: [corvette-ingest/ingestSkill.md:190](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:190), [corvette-ingest/ingestSkill.md:191](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:191), [corvette-ingest/ingestSkill.md:194](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:194), [corvette-ingest/ingestSkill.md:226](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:226), [corvette-build/buildSkill.md:292](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:292)

`option_kind` is enumerated, but there is no deterministic rule for inferring it for non-color RPOs. `section` is single-valued even though the same RPO can appear on multiple source sheets. `compat_note_text` is later build's first note source, but ingest never defines whether that field contains a resolved footnote, an in-cell numbered disclosure, row prose, or some mixture of those.

Impact: the same source can be classified differently across runs, and build can end up promoting rules out of heterogeneous note types without knowing it.

Recommendation: add deterministic inference and precedence rules for `option_kind`, `section`, and `compat_note_text` population.

5. **The Color and Trim handoff is not a closed ingest-to-build schema contract.**

Evidence: [corvette-ingest/ingestSkill.md:124](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:124), [corvette-ingest/ingestSkill.md:132](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:132), [corvette-ingest/ingestSkill.md:145](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:145), [corvette-build/buildSkill.md:139](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:139), [corvette-build/buildSkill.md:146](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:146), [corvette-build/buildSkill.md:190](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:190)

Ingest outputs treatment-level structures such as `interior_color_treatment_name`, `combo_source`, and `requires_rpos`, while build expects `interior_color_rpo`, `source_sheet_origin`, and `auto_added_rpos` on variant-ready rows. The Color and Trim outputs also carry trim, but not explicit `model_family` or `body_style`, which makes cross-family scoping underdefined.

Impact: build cannot join an interior selection to a pair-grid row or determine final variant scope without extra undocumented transformations.

Recommendation: either enrich ingest outputs with canonical variant-scoping fields and canonical auto-add fields, or explicitly document the exact normalization step build must perform before consuming them.

6. **`<Variant> Options` row generation is not specified as a repeatable algorithm.**

Evidence: [corvette-build/buildSkill.md:84](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:84), [corvette-build/buildSkill.md:116](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:116), [corvette-build/buildSkill.md:300](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:300), [corvette-build/buildSkill.md:335](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:335), [corvette-build/buildSkill.md:343](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:343)

The build skill says to duplicate rows when behavior changes, but it never writes down the derivation process from `Availability Long` and `Pricing Long` into final option rows. It also leaves open when a difference in availability, price, standardness, or note-derived logic should split a row rather than extend a scope field.

Impact: two correct builders can produce different row counts and different scopes for the same variant.

Recommendation: define a strict pipeline: group by RPO within variant, derive base scopes from `Availability Long`, merge pricing contexts from `Pricing Long`, promote explicit note logic, then split rows whenever price, standard flags, auto-adds, or rule fields differ.

7. **Build's UI-control fields are mandatory, but the skill does not define how to author them.**

Evidence: [corvette-build/buildSkill.md:91](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:91), [corvette-build/buildSkill.md:92](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:92), [corvette-build/buildSkill.md:93](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:93), [corvette-build/buildSkill.md:94](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:94), [corvette-build/buildSkill.md:95](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:95), [corvette-build/buildSkill.md:240](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:240)

`step_key`, `group_key`, `choice_mode`, `display_order`, and `ui_mode` are all required, but the skill does not define a canonical mapping from ingest data to those fields. It also does not say whether `auto_only` rows should still appear in the UI, be summary-only, or stay hidden until pricing/summary.

Impact: the stepped form cannot be generated consistently, even if the underlying compatibility logic is correct.

Recommendation: define a canonical authoring taxonomy for those fields, including default mappings from `section` and `option_kind`, ordering rules, and explicit `auto_only` display behavior.

8. **The exterior-paint build contract is incomplete.**

Evidence: [corvette-ingest/ingestSkill.md:166](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:166), [corvette-build/buildSkill.md:175](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:175), [corvette-build/buildSkill.md:179](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:179), [corvette-build/buildSkill.md:183](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:183), [corvette-build/buildSkill.md:238](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:238)

Ingest says Color and Trim is authoritative for paint identity and the matrix sheets are authoritative for per-variant availability, but build never spells out how those two sources merge into `<Variant> Exterior` section 3a. That section also lacks explicit body/trim scope columns even though runtime filters paint rows by body and trim.

Impact: build cannot represent paint availability and pricing contexts losslessly, and the source of truth for paint identity vs. paint availability is only implied.

Recommendation: explicitly define the source fusion for paint rows and add scope fields for body and trim on section 3a.

9. **The seat-first runtime flow does not guarantee the default seat path exists.**

Evidence: [corvette-build/buildSkill.md:78](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:78), [corvette-build/buildSkill.md:79](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:79), [corvette-build/buildSkill.md:141](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:141), [corvette-build/buildSkill.md:251](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:251), [corvette-build/buildSkill.md:254](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:254)

The runtime says interior flow starts by reading seat rows from `<Variant> Options`, but the build guidance only gives examples of seat upgrades such as `AH2` and `AE4`. It never explicitly requires rows for included/default seat states.

Impact: the build can correctly represent upgrade seats while still failing to offer the default seat path that unlocks the base interior matrix.

Recommendation: require one seat row per selectable seat state, including standard seats, or explicitly state that the default seat is derived somewhere other than `<Variant> Options`.

10. **The D30/R6X price-collapse case is acknowledged but not operationalized.**

Evidence: [corvette-ingest/ingestSkill.md:102](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:102), [corvette-ingest/ingestSkill.md:104](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:104), [corvette-ingest/ingestSkill.md:162](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:162), [corvette-build/buildSkill.md:320](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:320), [corvette-build/buildSkill.md:366](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:366)

The skills agree that both codes can land on the build while only one charge survives, but they never define the actual row pattern or precedence rule that produces the correct net price.

Impact: the highest-complexity interior/exterior combinations still require undocumented builder judgment.

Recommendation: add an explicit build-time pricing rule for the `D30|R6X` overlap case.

11. **`Ingest Exceptions` are not part of the build stop/go contract.**

Evidence: [corvette-ingest/ingestSkill.md:268](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:268), [corvette-ingest/ingestSkill.md:279](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:279), [corvette-ingest/ingestSkill.md:323](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:323), [corvette-build/buildSkill.md:50](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:50), [corvette-build/buildSkill.md:383](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:383)

Ingest defines an explicit exceptions sheet for unresolved items, but build never says whether it must read it, block on it, or proceed with warnings.

Impact: build can silently operate on incomplete ingest output, which defeats the purpose of the exception log.

Recommendation: define blocking vs. non-blocking exception categories and require build to stop when blocking ingest exceptions are present.

### High

12. **Equipment Groups do not yet have a defined flow through build.**

Evidence: [corvette-ingest/ingestSkill.md:3](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:3), [corvette-ingest/ingestSkill.md:190](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:190), [corvette-build/buildSkill.md:245](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:245)

Even if ingest captures Equipment Groups, build still does not say whether those groups become a selectable package step, a trim-bound auto-add bundle, or purely standard-equipment expansion.

Impact: trim/package inheritance can drift between variants because there is no shared rule for group handling.

Recommendation: add explicit Equipment Groups handling in build, including whether they generate selectable rows, auto-added child rows, or presentation-only expansions.

13. **Model-family coverage is inconsistent across the skill set.**

Evidence: [corvette-ingest/ingestSkill.md:3](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:3), [corvette-ingest/ingestSkill.md:22](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:22), [corvette-build/buildSkill.md:20](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:20), [corvette-build/buildSkill.md:28](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:28), [revBldSkill.md:157](/Users/seandm/Projects/27vette/corvette-build/revBldSkill.md:157)

Ingest explicitly handles `Grand Sport X`, the active build skill omits it, and the alternate build draft references `E-Ray` instead.

Impact: agents can build against the wrong canonical variant list or miss a family that ingest already treats as valid.

Recommendation: normalize the canonical model-family list across all Corvette skills and remove stale alternates.

14. **There is an internal contradiction in ingest around Color and Trim outputs.**

Evidence: [corvette-ingest/ingestSkill.md:122](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:122), [corvette-ingest/ingestSkill.md:145](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:145), [corvette-ingest/ingestSkill.md:166](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:166)

The Color and Trim section correctly defines `Color Combination Availability` as its own output, but line 166 says both matrix sheets and Color and Trim feed `Availability Long`.

Impact: that sentence can be read as instructing a duplicate write path or a second compatibility store in the wrong sheet.

Recommendation: correct that sentence so Color and Trim feeds `Option Catalog`, `Interior Trim Combos`, and `Color Combination Availability`, not `Availability Long`.

### Medium

15. **The workbook substrate is implied, but not explicitly named.**

Evidence: [corvette-ingest/ingestSkill.md:225](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:225), [corvette-ingest/ingestSkill.md:347](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:347), [corvette-build/buildSkill.md:61](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:61)

The skills clearly assume sheet-based storage, workbook-style outputs, and cell references such as `Interior 1!D4`, but they never explicitly say whether the operating substrate is Excel, Google Sheets, or a hybrid export/import workflow.

Impact: the correct agent workflow and practical limits depend on the substrate.

Recommendation: name the canonical substrate and any operational constraints that matter to ingestion/build.

16. **Model-year isolation is only partially defined.**

Evidence: [corvette-ingest/ingestSkill.md:184](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:184), [corvette-ingest/ingestSkill.md:346](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:346), [corvette-build/buildSkill.md:70](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:70)

Ingest says each model year gets its own workbook, but IDs such as `opt_<rpo>` and shared outputs such as `Base Prices` do not include an explicit year dimension.

Impact: if more than one model year ever coexists in one workbook or one downstream pipeline, collisions and ambiguous joins become possible.

Recommendation: explicitly state whether workbook boundaries are guaranteed year-isolation boundaries, or add year namespacing to IDs and output sheets.

17. **Rerun behavior is not fully specified.**

Evidence: [corvette-ingest/ingestSkill.md:338](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:338), [corvette-ingest/ingestSkill.md:340](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:340), [corvette-ingest/ingestSkill.md:347](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkill.md:347), [corvette-build/buildSkill.md:381](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:381), [corvette-build/buildSkill.md:385](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:385)

Both skills say to write generated sheets, but they do not define whether reruns replace, append, or patch prior generated sheets.

Impact: incremental refreshes become risky and manual cleanup becomes part of the process.

Recommendation: define whether reruns are full rebuilds, replace-in-place of generated sheets, or supported as partial patch passes.

18. **Validation examples need a minimum coverage rubric.**

Evidence: [corvette-build/buildSkill.md:353](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:353), [corvette-build/buildSkill.md:360](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:360), [corvette-build/buildSkill.md:364](/Users/seandm/Projects/27vette/corvette-build/buildSkill.md:364)

The build skill requires at least three end-to-end sample builds, but it does not define which hard cases those samples must cover.

Impact: an easy three-sample set can pass while the hardest cases remain untested.

Recommendation: require minimum coverage across at least these cases: standard seat path, package-dependent pricing split, D30-only color override, R6X plus D30 collapsed-pricing case, and one additive interior option gated by base interior.

## Recommended Next Edits

If the goal is to make these skills executable without hidden tribal knowledge, the next edits should happen in this order:

1. Finish ingest's source contracts: legend mapping, Standard Equipment, Equipment Groups, price-schedule shape, `price_mode`, `option_kind`, and note provenance.
2. Close the Color and Trim handoff: add missing scoping fields or define the exact normalization transform build must perform.
3. Finish build's generation algorithm: row-splitting rules, `step_key`/`group_key`/`choice_mode`/`display_order`/`ui_mode` authoring rules, paint-source fusion, and standard-seat handling.
4. Add cross-skill operating rules: `Ingest Exceptions` gating, canonical model-family list, rerun behavior, and model-year/workbook boundaries.

## Bottom Line

The skills already communicate the right philosophy. What they still need is a complete executable contract. Right now the missing pieces are not conceptual; they are procedural. Until those procedural gaps are written down, successful execution still depends on Sean or the operator supplying unstated rules in the middle of the run.
