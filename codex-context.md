# 27vette Current Context

## Current Status

- Stingray and Grand Sport are live customer-facing forms at `order.stingraychevroletcorvette.com`.
- Both live forms support build download and active dealer submission.
- The app is a static browser runtime backed by generated data in `form-app/data.js`.
- `window.CORVETTE_FORM_DATA` is the active multi-model registry.
- `window.STINGRAY_FORM_DATA` remains as a legacy alias for older Stingray tests/runtime expectations.
- `stingray_master.xlsx` is the canonical workbook for current business data and generated workbook sheets.
- The current architecture is in transition: business rules are being decoupled from Python/JavaScript and moved into workbook-authored source tables.
- Grand Sport is further along in the model-scoped workbook migration. Stingray still has remaining transitional generator/runtime logic that should be retired through scoped passes.

## Architecture Summary

```text
stingray_master.xlsx
  -> source sheets
  -> scripts/corvette_form_generator shared helpers
  -> scripts/generate_stingray_form.py production app-data writer
  -> scripts/generate_grand_sport_form.py Grand Sport inspection/draft writer
  -> generated form_* workbook sheets
  -> form-output artifacts
  -> form-app/data.js registry
  -> form-app static runtime
```

The workbook should own business data. Scripts should read, validate, normalize, and emit. Runtime code should render and evaluate generated data.

## Important Files

- `README.md` - project overview and architecture.
- `AGENTS.md` - detailed developer workflows and rules.
- `codex-context.md` - this short operational context.
- `stingray_master.xlsx` - canonical source workbook.
- `form-app/index.html` - static page shell and dealer submission modal.
- `form-app/styles.css` - app styling.
- `form-app/app.js` - model switching, runtime state, rule evaluation, pricing, rendering, downloads, and dealer submission.
- `form-app/data.js` - generated model registry.
- `form-output/stingray-form-data.json` - generated Stingray JSON contract.
- `form-output/stingray-form-data.csv` - generated Stingray CSV inspection/export artifact.
- `form-output/inspection/` - Grand Sport inspection, contract preview, rule audit, and draft artifacts.
- `scripts/generate_stingray_form.py` - production generator for workbook form sheets and app data.
- `scripts/generate_grand_sport_form.py` - Grand Sport inspection/draft generator; does not directly mutate app data.
- `scripts/corvette_form_generator/model_configs.py` - Stingray and Grand Sport model configuration.
- `scripts/corvette_form_generator/workbook.py` - workbook helpers, including safe save behavior.
- `tests/` - current regression and contract tests.

## Source-Of-Truth Rules

- Business rules belong in workbook rows when the workbook can represent them.
- Python should not accumulate model-specific RPO exceptions.
- JavaScript should not become the source of Corvette product rules.
- Correct bad source data in the workbook rather than hiding it in generator/runtime code.
- Keep Stingray and Grand Sport structurally consistent unless there is an explicit documented exception.
- Generated `form_*` sheets are output surfaces, not hand-edit surfaces.

## Decoupling Progress

Already workbook-backed or actively represented in generated data:

- variant matrix and model registry
- steps, sections, and context choices
- user-selectable choices and standard equipment
- explicit rules
- grouped rules
- exclusive groups
- price rules
- interiors
- color overrides
- validation rows

Remaining transitional seams:

- `scripts/generate_stingray_form.py` is still the production app-data writer and contains Stingray-specific normalization paths.
- `scripts/generate_grand_sport_form.py` still uses inspection/draft naming even though Grand Sport is live in the deployed app.
- Some generated Grand Sport metadata may still contain draft/inspection language. Inspect active registry data and tests before drawing conclusions from artifact names.
- Some runtime behavior in `form-app/app.js` still combines generic mechanics with legacy model-specific assumptions. Do not expand this pattern.

## Hard Boundaries

- Do not alter live app behavior unless explicitly requested.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior without approval.
- Do not add new dependencies without approval.
- Do not use bare system Python for generators.
- Do not edit generated workbook `form_*` sheets by hand.
- Do not write workbook changes while Excel has the workbook open.
- Do not ignore `~$stingray_master.xlsx`.
- Do not claim workbook edits landed without verifying the saved workbook on disk.
- Do not stage temporary workbook backups or unrelated generated output.

## Validation Commands

Use the project virtual environment:

```sh
cd <repo-root>
.venv/bin/python scripts/generate_stingray_form.py
```

Stingray tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Grand Sport inspection/draft refresh:

```sh
.venv/bin/python scripts/generate_grand_sport_form.py
```

Grand Sport tests:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Multi-model runtime test:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
```

Docs-only validation:

```sh
git diff -- README.md AGENTS.md codex-context.md
rg -n "draft[_]not[_]runtime[_]active|not runtime activ[e]|Stingray onl[y]|python3 scripts/generate_stingray_form[.]py" README.md AGENTS.md codex-context.md
```

## Current Priorities

- Continue moving business logic from code into workbook-authored tables.
- Keep generator scripts boring and model-general.
- Maintain live Stingray and Grand Sport behavior while decoupling rules.
- Improve workbook validation and model promotion gates.
- Add image assets to selectable options through workbook/generated data.
- Reduce customer-facing information overload without losing dealer handoff accuracy.
