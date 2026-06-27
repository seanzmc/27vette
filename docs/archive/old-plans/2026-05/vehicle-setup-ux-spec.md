# Vehicle Setup UX Consolidation Spec

Branch verified: `hermes/hermes-62195f2e` in `/Users/seandm/Projects/27vette/.worktrees/hermes-62195f2e`; not `main`.

## Goal

Make the first three setup decisions — Model, Body Style, and Trim Level — feel like one intentional "choose your Corvette" foundation step instead of three sparse, choppy screens.

## Diagnosis

Change type: runtime-only UX/behavior + styling + tests. No workbook write planned for this pass.

Root cause:
- The runtime currently exposes model selection as an injected runtime-only step (`modelStep`) and body/trim as generated context steps, so the first user-facing sequence is `model -> body_style -> trim_level`.
- Each of the first three steps is a small selection surface inside a large app shell. Body Style has only two text cards; Trim Level has three cards that wrap awkwardly in the current grid. This makes the flow feel like multiple interruption screens rather than one base-vehicle decision.
- The summary rail immediately shows a fully defaulted variant (`Corvette Stingray Coupe 1LT`) while the user is still being asked to choose Model, Body Style, then Trim Level. That makes defaults feel hidden/premature.
- The right rail exposes dense technical RPO information before the user has consciously finished choosing the base vehicle.

Evidence inspected:
- `form-app/app.js`
  - `modelStep` lines 97-100 injects a runtime-only `model` step ahead of generated workbook steps.
  - `rebuildDataIndexes()` line 145 builds `runtimeSteps = [modelStep, ...data.steps]`.
  - `currentStepIndex()`, `nextStep()`, `activateStep()`, `goToNextStep()` lines 398-444 currently navigate through every runtime step in order.
  - `renderContextCard()` lines 1570-1588 renders both body style and trim cards with the same card treatment.
  - `renderModelCard()` lines 1603-1621 renders only model cards on the model step.
  - `renderStepContent()` lines 1805-1920 branches separately for model, context body/trim, and option steps.
  - `handleContextChoice()` lines 1324-1332 already updates body/trim generically from context choice rows.
  - `resetModelScopedState()` lines 2455-2464 resets a model switch back to the default first variant and `activeStep = "model"`.
- `form-app/styles.css`
  - `.choice-grid` lines 311-315 uses `repeat(auto-fill, minmax(250px, 1fr))`, causing 3 trim cards to lay out as 2 + 1 at the inspected viewport.
  - `.choice-card.selected` lines 515-519 relies mainly on red border/inset border; there is no explicit selected label/checkmark.
  - `.step-footer` lines 283-290 right-aligns the Next button away from sparse early choices.
- `form-app/data.js` runtime data inspection:
  - Both Stingray and Grand Sport have exactly 6 variants: Coupe/Convertible x 1LT/2LT/3LT.
  - Body style context choices currently have no images/tooltips and descriptions like `3 trims available`.
  - Trim context choices have price and tooltip copy but no images.
- Browser inspection at local `form-app` server:
  - Step 1 shows two model cards and a detached `Next: Body Style` CTA.
  - Step 2 shows two sparse body cards and a detached `Next: Trim Level` CTA while the summary already says `Corvette Stingray Coupe 1LT`.
  - Step 3 shows three trim cards in an imbalanced 2+1 layout plus a dense Standard & Included block.
- `codex-context.md` confirms runtime is static app backed by generated data; business rules belong in workbook rows; current priority includes reducing customer-facing information overload.
- Existing tests:
  - `tests/stingray-form-regression.test.mjs` has runtime/source assertions for scroll and rendering helpers.
  - `tests/multi-model-runtime-switching.test.mjs` exposes runtime helpers and already tests `renderContextCard()`, model switching, summary/export/dealer payload behavior.

Risk level: medium.
- This changes visible navigation and first-step behavior for the live customer app.
- It should not change pricing, rules, selected option reconciliation, exports, dealer submission payloads, generated workbook sheets, or generated app-data structure.

## Proposed UX

Use one visible first step: `Vehicle Setup`.

On that step, render three connected selection groups:
1. Model: Stingray / Grand Sport
2. Body Style: Coupe / Convertible
3. Trim Level: 1LT / 2LT / 3LT for the selected body style

Then the primary CTA should continue directly to `Exterior Paint`.

The generated `body_style` and `trim_level` steps remain in `data.steps` and `form-app/data.js`, but the runtime treats them as subchoices inside `model` for navigation/display. This keeps business data ownership intact while improving the user-facing flow.

Expected customer-facing behavior:
- Left rail first item becomes `Vehicle Setup`; `Body Style` and `Trim Level` are not separate visible rail stops.
- Mobile progress counts visible setup as one step, then continues to Exterior Paint.
- Main first page explains the default start, e.g. "We've started you with Stingray Coupe 1LT. Adjust the foundation of your build before choosing paint."
- Model/body/trim cards show explicit selected affordances (`Selected` / checkmark style), not only a border.
- Body style cards show clearer availability copy from existing data plus available trims derived from variants, e.g. `Available with 1LT, 2LT, 3LT`.
- Trim cards show price, current model/body description, and tooltip/details copy already present in generated context choices.
- `Continue to Exterior Paint` replaces `Next: Body Style` / `Next: Trim Level` on the setup screen.
- The right summary remains available, but the main setup screen should contain a lightweight "Build starts as" / base MSRP callout so the default does not feel hidden.

## Exact files to change

Runtime/styling:
- Modify `form-app/app.js`
  - Change `modelStep.step_label` from `Model` to `Vehicle Setup`.
  - Add helpers for visible navigation steps, likely:
    - `vehicleSetupStepKeys`
    - `visibleRuntimeSteps()` or equivalent
    - `normalizeVehicleSetupStep(stepKey)` so direct attempts to activate `body_style`/`trim_level` route to `model`.
  - Update `currentStepIndex()`, `nextStep()`, `currentStepSummary()`, and `renderStepRail()` to use visible steps, not raw generated `runtimeSteps`, for user navigation.
  - Keep raw `runtimeSteps` available for rule detail labels and generated data lookup where needed.
  - Add helper renderers for the setup page, likely:
    - `bodyStyleContextChoices()`
    - `trimLevelContextChoices()`
    - `availableTrimLabelsForBodyStyle(bodyStyle)`
    - `renderVehicleSetupGroup(...)`
    - `renderVehicleSetupSummary()`
    - `renderVehicleSetupContent()`
  - Reuse `renderModelCard()` and `renderContextCard()` where safe, but add setup-specific wrappers/classes so card layout can be improved without affecting later option grids.
  - Update setup CTA so `model` step advances to the first visible post-setup step (`paint`).
  - Preserve `handleContextChoice()` state behavior and model switching confirmation behavior.
- Modify `form-app/styles.css`
  - Add vehicle setup layout styles (`.vehicle-setup-section`, `.vehicle-setup-grid`, `.vehicle-setup-group`, `.vehicle-setup-summary`, `.setup-choice-grid`, etc.).
  - Add explicit selected affordance styles (`.selection-status`, check/selected pill) for model/context cards, either globally or setup-scoped.
  - Make trim cards lay out evenly in setup (`repeat(3, minmax(...))` on desktop, stacked on mobile) without disrupting existing option card grids.
  - Keep existing visual system: beige panels, red accent, current type scale, existing buttons.

Tests:
- Modify `tests/multi-model-runtime-switching.test.mjs`
  - Expose any new helper needed for assertions, if necessary.
  - Add/adjust tests that assert:
    - visible navigation renders `Vehicle Setup` and does not render separate rail buttons for `Body Style` / `Trim Level`.
    - `goToNextStep()` or setup CTA moves from `model` to `paint`, not `body_style`.
    - selecting Convertible / 2LT inside setup updates `state.bodyStyle`, `state.trimLevel`, summary/export/dealer payload exactly as before.
    - model switch still resets to selected model default variant and stays on setup.
    - `renderContextCard()` still supports existing tooltip/media behavior.
- Modify `tests/stingray-form-regression.test.mjs` only if source/string assertions need updating for the new helper names or visible copy.

Potentially no changes:
- `form-app/index.html` unless markup shell needs a new static hook. Prefer no change.
- `form-app/data.js` no hand edits.
- `form-output/` no hand edits.
- `stingray_master.xlsx` no workbook writes.
- `scripts/` no generator changes unless implementation reveals a data gap that must be workbook/generator-owned. If so, stop and respec before writing workbook/generator changes.

## Constraints

- Visual preservation: stay within the current app visual language; improve hierarchy/engagement without redesigning the whole app shell.
- No broad refactor: keep changes localized to first-step rendering/navigation and supporting tests/styles.
- No new dependencies.
- Workbook source-of-truth: do not hardcode Corvette product/business claims in JS. Use existing generated model/variant/context-choice data for labels, prices, trims, and tooltips. Any future richer body-style imagery/copy should be workbook/generator-owned in a separate pass.
- Do not edit generated `form_*` workbook sheets manually.
- Do not hand-edit `form-app/data.js` or `form-output/` for this pass.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, download schema, pricing, rules, auto-add logic, or selected-RPO computation.
- Preserve Stingray and Grand Sport parity.
- Preserve direct reset/model-switch confirmation safeguards.

## Risks

- Tests may assume raw `runtimeSteps` count/order. Update only user-visible navigation expectations, not generated data contracts.
- Hidden body/trim navigation could break code paths that use `stepKey` from missing requirement details. Mitigation: only hide `body_style`/`trim_level` in visible navigation; keep raw steps for data lookups and route direct activation of those keys to `model`.
- Model switching invokes reset confirmation when `activeStep !== "model"`; after this pass fewer setup interactions leave `activeStep = model`, so changing model during setup may not prompt if no later changes exist. This is acceptable if no user option/interior selections exist; confirm tests around userSelected/interior/later step still prompt.
- The right rail remains dense. This pass improves the main setup experience first; deep right-rail simplification should be a follow-up if desired.

## Non-goals

- No workbook data migration.
- No body-style image sourcing or new media asset mapping in this pass.
- No summary rail redesign beyond any copy needed to support the setup screen.
- No changes to option-rule semantics, prices, export content, dealer submission payloads, or model registry structure.
- No deployment or production publish step.

## Validation plan

Pre-implementation check:
```sh
git branch --show-current
git status --short --branch
```

Targeted runtime gates:
```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
```

Full current suite if targeted gates pass:
```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual/browser verification:
```sh
cd form-app
/Users/seandm/Projects/27vette/.venv/bin/python -m http.server 8000
```
Then verify:
- First visible step is Vehicle Setup.
- Model/body/trim choices are all available on the first screen.
- Continue goes to Exterior Paint.
- Switching Stingray/Grand Sport resets to the corresponding default variant and updates setup cards/summary.
- Coupe/Convertible and 1LT/2LT/3LT update pricing and summary immediately.
- Build download and dealer submission payload still include model, body_style, trim_level, variant_id, and price as before.
- Mobile viewport still has usable progress/navigation.

## Approval

This spec is ready for implementation. Because this is a non-trivial live-runtime behavior change, AGENTS.md requires approval before edits beyond the spec. Suggested approval phrase: `approved: implement vehicle setup UX spec`.
