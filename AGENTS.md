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
