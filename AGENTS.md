# Agent Instructions for 27vette

## Project validation

Use the project virtual environment for Python commands.

Do not run the workbook generator with bare system Python:

`python3 scripts/generate_stingray_form.py`

Instead, run:

`.venv/bin/python scripts/generate_stingray_form.py`

Or activate the virtual environment first:

`source .venv/bin/activate`

Then run:

`python scripts/generate_stingray_form.py`

Then run the regression tests:

`node --test tests/stingray-form-regression.test.mjs`

## Dependency setup

If `.venv` does not exist, create it from the repo root:

`python3 -m venv .venv`

`source .venv/bin/activate`

`python -m pip install --upgrade pip`

`python -m pip install -r requirements.txt`

Do not commit `.venv/`.

## Behavioral Guidelines

- Don't assume. Don't hide confusion. Surface tradeoffs.
- Minimum code that solves the problem. Nothing speculative.
- Touch only what you must. Clean up only your own mess.
- Define success criteria. Loop until verified.

## Workbook source-of-truth policy

- Treat workbook sheets as the source of truth for Corvette business data: option placement, active/selectable/display behavior, display order, descriptions/disclosures, explicit rules, exclusive groups, package includes, price overrides, color overrides, and variant status.
- Do not hide business rules in generator/runtime scripts when they can be represented as workbook data. If a script is needed to apply a cleanup, prefer writing the corrected rows back to the workbook source, then have generators consume those rows.
- Keep each model structurally consistent from raw workbook sheets through scripts to front-end artifacts. Models may differ in options and compatibility, but they should use the same sheet shapes, rule concepts, and output contracts unless there is an explicit documented exception.
- Use scripts for normalization, artifact emission, validation, audits, and runtime mechanics such as applying workbook-authored includes/requires/excludes, exclusive groups, auto-adds, filtering, and pricing.
- Flag any proposed hardcoded model-specific business logic before implementing it.
