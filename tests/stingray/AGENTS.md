# Agent Instructions for tests/stingray

## Test workflow

Use focused RED-first tests for implementation passes.

- Add or update the narrowest affected `tests/stingray/*` file first.
- Run the focused test before broad suites.
- Run adjacent control-plane tests when touching ownership, package projection, rule-only IDs, production-guarded refs, preserved cross-boundary refs, or interior source namespaces.
- Run the full Stingray ladder before claiming completion for broad migration or behavior changes.

## Scope rules

- Tests should preserve production behavior as the oracle.
- CSV-shadow tests must not imply cutover.
- Do not update tests to bless shadow behavior that differs from production unless the task explicitly approves the difference and documents it.
- Keep assertions tied to concrete RPOs, option IDs, group IDs, or runtime scenarios.

## Common commands

Focused test:

`node --test tests/stingray/<test-file>.test.mjs`

Production safety checks when production generator/app behavior is touched:

`node --test tests/stingray-form-regression.test.mjs`

`node --test tests/stingray-generator-stability.test.mjs`
