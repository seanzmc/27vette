# Agent Instructions for scripts

## Python execution

Use the project virtual environment for Python commands:

`.venv/bin/python <script>`

Do not run project scripts with bare system Python.

## Production generator boundary

`scripts/generate_stingray_form.py` is the production workbook-to-app generator.

- Do not change it during CSV-shadow migration work unless explicitly approved.
- If the production generator changes or generated artifacts must be refreshed, run:

`.venv/bin/python scripts/generate_stingray_form.py`

Then run:

`node --test tests/stingray-form-regression.test.mjs`

## CSV-shadow scripts

`scripts/stingray_csv_first_slice.py`, `scripts/stingray_csv_shadow_overlay.py`, and `scripts/build_stingray_experimental_app.py` support shadow/experimental migration work.

- Shadow scripts must not overwrite production `form-app/data.js`.
- Experimental app output belongs under `build/experimental/form-app/`.
- Preserve production-shaped output unless a contract change is explicitly approved.
- Keep validation failures loud; do not quiet unresolved ownership or structured-reference problems.

## Scope control

Avoid broad script refactors during migration passes. Prefer the smallest change tied to the approved pass, focused test, and ownership boundary.
