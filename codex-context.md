# 27vette Current Context

## Current status
- Stingray functional baseline is stable.
- Multi-model registry is active.
- Grand Sport runtime loads.
- Grand Sport interiors are populated.
- Current phase: Grand Sport exclusive groups.

## Validation commands
`.venv/bin/python scripts/generate_stingray_form.py`
`node --test tests/stingray-form-regression.test.mjs`
`node --test tests/grand-sport-draft-data.test.mjs`
`node --test tests/multi-model-runtime-switching.test.mjs`

## Hard boundaries
- Do not alter Stingray behavior.
- Do not wire Formidable.
- Do not change runtime unless explicitly approved.
- Prefer model config/generator data changes.

## Current task
Add Grand Sport exclusiveGroups only.
