# Architectural Review: Repeatability and Modularity for Adding New Corvette Models

## Scope and evidence note

I was able to access the public `seanzmc/27vette` repository and reviewed the current `main` branch, focusing on `scripts/`, `form-app/`, `form-output/`, root workflow/data files, and the available test and inspection artifacts. Because the Grand Sport work appears to be actively evolving, treat the Grand Sport-specific counts below as a snapshot of the checked-in artifacts, not as a guarantee that every branch or local working copy is identical. ([github.com](https://github.com/seanzmc/27vette))

## Executive assessment

The system is **strongest as a repeatable Stingray workbook-to-static-app pipeline** and **promising but not yet fully production-repeatable for additional models**. The static app has a real multi-model registry pattern, and the UI/runtime are largely data-driven. However, runtime state handling is still procedural and includes Corvette/Stingray-specific assumptions, while the data contract is implicit rather than formally schema-governed. ([github.com](https://github.com/seanzmc/27vette))

**Overall readiness to add a new model with a similar option-guide structure: 6 / 10.** The best summary is: **Stingray-production-ready, multi-model-preview/partial-runtime-ready, but not yet multi-model-production-repeatable.** Grand Sport demonstrates that the architecture can ingest a similar model surface, but rule coverage, pricing semantics, cleanup, and activation governance still need hard gates before another model can be trusted for production ordering. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-form-data-draft.md))

## Priority ratings

| Priority               |       Rating | Architect-level readout                                                                                               |
| ---------------------- | -----------: | --------------------------------------------------------------------------------------------------------------------- |
| **State management**   | **5.5 / 10** | Centralized and understandable, but mutable, side-effect-heavy, and not modeled as a deterministic transition system. |
| **Schema flexibility** |   **6 / 10** | Broad generated contract exists, but the schema is implicit and unevenly validated across models.                     |
| **Component reuse**    |   **7 / 10** | Shared UI/rendering is effective; reuse is limited by hardcoded model shell details and monolithic runtime logic.     |

---

# Workflow and data-management review

## Current workflow pattern

The documented active workflow is clear for Stingray: `stingray_master.xlsx` is the source of truth, `scripts/generate_stingray_form.py` regenerates workbook `form_*` sheets, `form-output/stingray-form-data.json`, `form-output/stingray-form-data.csv`, and `form-app/data.js`, and the static app runs without a build step. The README also documents the local setup and regression command. ([github.com](https://github.com/seanzmc/27vette))

`App-refresh-workflow.md` strengthens repeatability for Stingray: it identifies generated artifacts, says frontend runtime files usually should not change during a data refresh, requires generator execution, regression testing, timestamp/text spot checks, manual app checks, diff review, and stopping if validation errors are nonzero. That is good process governance for the current model. ([github.com](https://github.com/seanzmc/27vette/blob/main/App-refresh-workflow.md))

## Script-layer modularity

The `scripts/` directory now has more than a one-off generator: it includes `generate_stingray_form.py`, `generate_grand_sport_form.py`, `generate_form.sh`, and a shared `corvette_form_generator` package with `inspection.py`, `mapping.py`, `model_config.py`, `model_configs.py`, `output.py`, `validation.py`, and `workbook.py`. This is a meaningful modularity improvement because model configuration, workbook utilities, output writing, mapping, and validation are at least partially separated. ([github.com](https://github.com/seanzmc/27vette/tree/main/scripts))

That said, the Stingray generator remains a large, model-centered production script: GitHub reports it as **1,274 lines / 1,184 LOC**, and it still imports `STINGRAY_MODEL`, reads specific workbook sheets such as `variant_master`, `category_master`, `section_master`, `option_variant_status`, `rule_mapping`, `price_rules`, `lt_interiors`, `LZ_Interiors`, and `PriceRef`, and has Stingray-specific validation expectations such as six active variants. ([github.com](https://github.com/seanzmc/27vette/blob/main/scripts/generate_stingray_form.py))

The Grand Sport generator is explicitly a **read-only scaffold**: it calls inspection, contract-preview, and draft-data artifact builders rather than writing directly to the production app. That is architecturally safe, but it also confirms Grand Sport onboarding is not yet equivalent to the Stingray production generator path. ([github.com](https://github.com/seanzmc/27vette/blob/main/scripts/generate_grand_sport_form.py))

## Form app runtime pattern

The app has a good multi-model foundation: `app.js` builds a `CORVETTE_FORM_DATA` registry, tracks `activeModelKey`, `activeModel`, and `data`, and rebuilds runtime indexes for steps, variants, sections, choices, interiors, rules, price rules, rule groups, and exclusive groups. That is the right architectural direction for adding models with similar option-guide structures. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

The static shell still exposes hardcoded model choices — the current rendered `index.html` surface shows “Model Stingray Grand Sport” — so adding a third model is not yet fully registry-driven at the UI shell level. That is a small but real modularity leak. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/index.html))

---

# State-management evaluation — **5.5 / 10**

## What works

State is centralized in one global object with body style, trim level, selected option IDs, user-selected option IDs, selected interior, active step, and customer information. Runtime indexes are rebuilt from the active model dataset, which gives the app a coherent way to switch model data and re-evaluate choices. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

A typical state transition is traceable:

1. **Model/data activation**: registry data is selected and indexes are rebuilt.
2. **Body/trim change**: `setBodyAndTrim()` updates context, calls `resetDefaults()`, then `reconcileSelections()`, then renders.
3. **Option selection**: `handleChoice()` checks auto-added status and disable reasons, mutates selected/user-selected sets, removes conflicts, reconciles, and renders.
4. **Interior selection**: `handleInterior()` toggles the selected interior, reconciles, and renders.
5. **Derived state**: `computeAutoAdded()`, `disableReasonForChoice()`, `missingRequired()`, `optionPrice()`, and `lineItems()` derive requirements, disabled states, pricing, summary rows, and exports. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

## What limits reliability across models

The state model is **procedural rather than declarative**. There is no reducer, state machine, event log, transition table, or pure rule-evaluation boundary. Instead, state changes are interleaved with reconciliation, defaulting, rule evaluation, pricing, and rendering. That works for a known dataset, but it is harder to prove correct when a new model introduces different packages, defaults, replacement semantics, required choices, or interior structures. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

There are still runtime hardcodes that should be data-owned. Examples include default RPO logic for `FE1`, `NGA`, and `BC7`; special replacement/conflict logic for `Z51`, `FE2`, `NWI`, `GBA`, and `ZYC`; section IDs such as `sec_susp_001` and `sec_seat_001`; and an interior component price exception around `R6X`. These may be valid for the current Stingray rules, but they reduce repeatability for new models. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

## State-management verdict

The state flow is understandable and centralized, but not yet robust enough to call multi-model-safe. The next architectural step is to move defaulting, replacement, package inclusion, and special-case RPO behavior into a model-scoped rules contract, then test state transitions as deterministic inputs and outputs.

---

# Schema-flexibility evaluation — **6 / 10**

## What works

The generated contract is broad and expressive. The runtime expects data surfaces for `steps`, `variants`, `sections`, `choices`, `rules`, `priceRules`, `ruleGroups`, `exclusiveGroups`, `interiors`, `colorOverrides`, context choices, standard equipment, and validation. This gives the app enough structural vocabulary to support additional models that resemble the Stingray option guide. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

The Grand Sport draft shows that the same general contract surface can be produced for another model: the draft artifact reports six variants, eight context choices, 14 steps, 34 sections, 1,614 choices, 545 standard-equipment rows, five model-scoped exclusive groups, and 132 model-scoped interiors. That is a meaningful proof of portability for the base option-guide shape. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-form-data-draft.md))

## What limits flexibility

The inbound schema appears to be **implicit**. I did not find a formal JSON Schema or typed contract that validates model datasets before they are accepted by the runtime. There is generator validation, and the Stingray workflow stops on validation errors, but that is not the same as a versioned, model-agnostic schema contract with required fields, field types, enum constraints, rule semantics, and compatibility checks. ([github.com](https://github.com/seanzmc/27vette/blob/main/App-refresh-workflow.md))

Grand Sport exposes the schema-flexibility gap. The checked-in draft explicitly marks rule groups, rules, price rules, and color overrides as deferred, while preserving 123 rule/detail hot-spot rows for later work. Current context says Grand Sport now has runtime data, populated interiors, and exclusive groups, but it still identifies rules, price rules, text cleanup, display order, and section placement as remaining cleanup areas. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-form-data-draft.md))

There is also evidence of stale or transitional inspection artifacts. An older Grand Sport cleanup audit, generated from the active registry on April 30, 2026 at 17:58 UTC, reports zero active Grand Sport rules, price rules, exclusive groups, rule groups, and interiors, while later context and draft artifacts indicate interiors and exclusive groups have since progressed. The architectural conclusion is not that one artifact is “wrong,” but that **promotion status must be machine-gated and regenerated** so production readiness is not inferred from stale inspection files. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-cleanup-audit.md))

## Schema-flexibility verdict

The schema is broad enough, but not governed enough. It can accommodate similar models if they follow the current shape, but it does not yet provide a strong, explicit contract for safely onboarding models with different default packages, interior decomposition, pricing exceptions, or compatibility rules.

---

# Component-reuse evaluation — **7 / 10**

## What works

The UI is largely data-driven. The app renders step rails, context cards, option cards, interior groups, standard equipment, summaries, selected RPOs, auto-added RPOs, missing requirements, customer information, and exports based on the active dataset. That is a strong component-reuse pattern for a static form app. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

The app also has a reusable static deployment model: `form-app/index.html`, `styles.css`, `app.js`, and `data.js` run without a build step. This simplicity is a strength for operational repeatability and low-friction handoff. ([github.com](https://github.com/seanzmc/27vette))

## What limits reuse

The reuse is concentrated in one large runtime file. Rendering, state transitions, rule evaluation, pricing, interior logic, export formatting, model switching, defaults, and DOM binding are all housed in `app.js`. This makes the UI reusable at the surface level, but it makes behavioral changes for a new model riskier because a small model-specific rule can require editing shared runtime code. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

The model selector is not fully generated from the registry in the shell. The displayed shell includes Stingray and Grand Sport directly, so new models still require UI shell review rather than being purely data-registered. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/index.html))

## Component-reuse verdict

Component reuse is the strongest of the three priorities, but it should be protected by modularizing the runtime into separate state, rule, pricing, interior, rendering, and export modules.

---

# SWOT analysis

## Strengths

- **Data-driven multi-model registry is already present.** The runtime can select an active model, swap the active dataset, and rebuild indexes for model-specific choices, rules, price rules, interiors, and groups. This is the core pattern needed for repeatable model onboarding. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

- **Stingray has a documented, repeatable source-to-app workflow.** The root workflow identifies `stingray_master.xlsx` as the source of truth, generated outputs, validation behavior, regression tests, manual checks, and expected commit files. ([github.com](https://github.com/seanzmc/27vette/blob/main/App-refresh-workflow.md))

- **Generated data contract is rich.** The runtime and generator support variants, steps, sections, choices, standard equipment, rules, price rules, exclusive groups, rule groups, interiors, color overrides, validation rows, and exportable summaries. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

- **Inspection artifacts are valuable.** Grand Sport preview, draft, cleanup audit, and inspection outputs preserve unresolved hot spots, counts, text cleanup candidates, section placement, and browser smoke notes. These are exactly the artifacts a technical architect needs before allowing a model to become production-selectable. ([github.com](https://github.com/seanzmc/27vette/tree/main/form-output/inspection))

- **Script package extraction is moving in the right direction.** The shared `corvette_form_generator` modules show a shift away from a purely one-off generator toward reusable mapping, config, output, validation, workbook, and inspection utilities. ([github.com](https://github.com/seanzmc/27vette/tree/main/scripts/corvette_form_generator))

## Weaknesses

- **State transitions are not formally modeled.** Mutating `Set`s and running layered reconciliation functions works for the current app, but it is harder to reason about than a pure transition model or reducer-based state machine. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

- **Runtime still contains model-specific business rules.** RPO-specific defaults and exceptions in `app.js` make the system less repeatable for models whose suspension, exhaust, color, seat, package, or interior rules differ from Stingray. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

- **Schema governance is implicit.** Generator validation exists, but there is no visible formal JSON Schema or versioned contract gate that prevents incomplete model data from rendering. ([github.com](https://github.com/seanzmc/27vette/blob/main/App-refresh-workflow.md))

- **Grand Sport is still incomplete for production use.** The latest context says Grand Sport runtime/interiors/exclusive groups have progressed, but it also says rules, price rules, text cleanup, display order, and section placement still require focused cleanup. The draft artifact explicitly defers rules and price rules. ([github.com](https://github.com/seanzmc/27vette/blob/main/codex-context.md))

- **App/runtime code is monolithic.** Component reuse exists, but business logic, state, DOM rendering, pricing, rules, and export behavior are not cleanly isolated. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

- **Automated tests exist, but CI is not evident from the reviewed tree.** The repository has a `tests/` folder with Stingray, Grand Sport, and multi-model tests, but no `.github/workflows` directory is visible in the root listing, so continuous enforcement is not clearly established. ([github.com](https://github.com/seanzmc/27vette/tree/main/tests))

## Opportunities

- **Create a formal model-data schema.** Add `schema/form-data.schema.json` or equivalent TypeScript/Zod/AJV validation covering required arrays, field types, enum values, rule types, price-rule semantics, interior component structure, validation severity, export schema version, and model activation status.

- **Move model-specific defaults and exceptions into data.** Defaults such as suspension, exhaust, seat, body-style-only defaults, replacement behavior, and package dependencies should be represented as model-scoped rules or metadata, not JavaScript branches.

- **Turn Grand Sport inspection artifacts into promotion gates.** A model should not be production-selectable until generated checks pass for required steps, interior coverage, rule coverage, price-rule coverage, exclusive-group coverage, validation errors, browser smoke checks, and export integrity. The existing inspection artifacts are already close to becoming those gates. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-form-data-draft.md))

- **Generate the model selector from the registry.** The UI shell should populate available models from `CORVETTE_FORM_DATA.models`, with a `status` or `productionReady` flag controlling whether draft models are hidden, disabled, or visibly marked as preview.

- **Split `app.js` into modules.** Suggested modules: `modelRegistry`, `stateMachine`, `ruleEngine`, `pricing`, `interiors`, `rendering`, `exports`, and `validationDisplay`.

- **Normalize all future models through the same source-data workflow.** The project’s own context says Grand Sport should be normalized to match the Stingray workbook/source-data workflow rather than handled through a separate schema or accumulating Python patches. ([github.com](https://github.com/seanzmc/27vette/blob/main/codex-context.md))

## Threats

- **A model can render before it is valid.** The biggest architectural risk is that a model may appear selectable and exportable while missing compatibility rules, pricing rules, interiors, or required package enforcement. The older cleanup audit’s Grand Sport smoke notes are a concrete example of this failure mode. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-cleanup-audit.md))

- **Rule complexity may outgrow ad hoc reconciliation.** Includes, excludes, requires-any groups, replacement actions, pricing overrides, color overrides, package dependencies, and interior component pricing will become harder to test if they remain spread across runtime branches and generated rows.

- **Stale inspection artifacts can mislead promotion decisions.** Current context and older audit artifacts disagree about Grand Sport runtime completeness because work has progressed. Without regeneration timestamps and activation gates, teams may make decisions from stale artifact state. ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-cleanup-audit.md))

- **Embedded `data.js` may become operationally awkward.** As more models are embedded into a single static data bundle, load time, diff review, merge conflicts, and rollback behavior may degrade. The current architecture is simple, but it should eventually support per-model data files or lazy loading.

- **Manual workflow can drift without CI.** The documented checklist is solid, but without visible CI enforcement, validation and regression testing depend on human discipline. ([github.com](https://github.com/seanzmc/27vette/blob/main/App-refresh-workflow.md))

---

# Repeatability verdict

## For Stingray

**Strong.** Stingray has a source workbook, a production generator, generated JSON/CSV/app data artifacts, regression guidance, validation checks, and a refresh checklist. This is repeatable enough for ongoing single-model maintenance. ([github.com](https://github.com/seanzmc/27vette))

## For Grand Sport and future similar models

**Partial.** The system can produce a Grand Sport preview/draft and has moved toward runtime support, but the current checked-in materials still identify deferred compatibility rules, price rules, cleanup, display ordering, and section-placement work. That means the system is not yet “drop in another option guide and go.” ([github.com](https://github.com/seanzmc/27vette/blob/main/form-output/inspection/grand-sport-form-data-draft.md))

## For modularity

**Moderate.** The runtime registry, generated contract, and shared generator utilities are promising. The main blockers are hardcoded runtime business rules, lack of a formal schema gate, incomplete model promotion rules, and monolithic app logic.

---

# Recommended architecture moves

1. **Add a versioned model-data contract.**  
   Define and validate a formal schema for each model dataset before it can enter `form-app/data.js`.

2. **Add model activation status.**  
   Every model should carry a status such as `draft`, `preview`, `runtime_test`, or `production`. The UI should hide or mark non-production models accordingly.

3. **Move RPO-specific behavior out of `app.js`.**  
   Convert defaults, replacements, required packages, includes/excludes, body-style scoping, and price overrides into model-scoped data.

4. **Modularize the runtime.**  
   Extract state transitions, rules, pricing, interiors, rendering, and export formatting into testable modules.

5. **Create transition-matrix tests.**  
   For each model, test body/trim switching, default reset, single-select replacement, multi-select conflict handling, package includes, required groups, interior compatibility, price overrides, and export payload completeness.

6. **Promote Grand Sport through gates.**  
   Before calling it production-ready, regenerate current inspection artifacts and require passing checks for interiors, rules, price rules, exclusive groups, rule groups, validation errors, smoke tests, and export correctness.

7. **Add visible CI.**  
   Run the generator and all Node tests on every pull request. Existing tests already cover Stingray regression, generator stability, Grand Sport preview/draft data, and multi-model runtime switching; they should become enforced gates. ([github.com](https://github.com/seanzmc/27vette/tree/main/tests))

8. **Plan for per-model data loading.**  
   Keep the no-build static app, but consider loading `data-stingray.js`, `data-grand-sport.js`, etc. on demand as model count grows.

---

# Bottom line

The repository has a solid foundation: a repeatable Stingray generation workflow, a data-driven static app, a multi-model registry, shared generator utilities, and useful inspection artifacts. The main architectural gap is that **model onboarding is not yet governed by a formal schema, deterministic state engine, and production activation gate**.

For a technical architect, the recommendation is to treat the current system as:

> **Production-ready for Stingray, credible for Grand Sport/future-model preview work, but not yet production-repeatable for arbitrary new models with similar option guides.**
