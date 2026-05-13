# Download Build Readiness And Standard Count Spec

## Diagnosis

Two customer-facing export issues remain after the Markdown download pass:

- `Download Build` is currently always clickable because `form-app/app.js` wires `els.downloadBuildButton.addEventListener("click", downloadBuild)` without checking `missingRequired()`.
- `downloadBuild()` calls `buildMarkdown()`, and `buildMarkdown()` currently appends:
  - `## Standard & Included`
  - `- {count} items`
- The standard item count is still useful in the sidebar and internal order contract, but it is not helpful in the customer-facing downloaded build.

Risk level: low. This is a front-end export/readiness behavior change only. It should not touch workbook rules or generated source data.

## Goal

1. Make `Download Build` unavailable while required selections remain open.
2. Remove the `Standard & Included` count from the downloaded Markdown.
3. Preserve standard equipment count in the sidebar and compact/internal order data.

## Files To Change

- `form-app/app.js`
- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Generated files should not need regeneration unless tests prove `data.js` must change.

## Implementation Plan

### Download Button State

In `renderSummary()` or a small helper it calls:

- Compute `const missing = missingRequired();`
- Set:
  - `els.downloadBuildButton.disabled = missing.length > 0`
  - `els.downloadBuildButton.title = missing.length ? "Complete required selections before downloading your build." : ""`
  - optionally `aria-disabled` through the native `disabled` state only.

In `downloadBuild()`:

- Defensively return without downloading if `missingRequired().length > 0`.

Expected behavior:

- Incomplete build: button is disabled and no file downloads.
- Complete build: button is enabled and downloads Markdown.

### Markdown Standard Count

In `buildMarkdown()`:

- Remove the block that emits:
  - `## Standard & Included`
  - `- {count} items`

Do not remove:

- `standard_equipment` from `compactOrder()`.
- `standard_equipment_summary` from `currentOrder()`.
- Sidebar `Standard & Included`.
- Plain text summary behavior unless separately requested.

## Tests

Update `tests/stingray-form-regression.test.mjs`:

- Add/adjust runtime test:
  - initial/incomplete build does not download when `downloadBuild()` is called.
  - after required selections are complete enough, `downloadBuild()` downloads `.md`.
  - Markdown does not include `Standard & Included`.
- Keep existing assertions that internal compact/current order preserve standard equipment count.

Update `tests/multi-model-runtime-switching.test.mjs`:

- Grand Sport Markdown should not include `Standard & Included`.
- Verify model-specific filenames still work when the build is complete.

## Validation Plan

Run:

```bash
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/stingray-generator-stability.test.mjs
git diff --check
```

Manual browser checks:

- `Download Build` is disabled before required choices are complete.
- Button enables once the build has no open requirements.
- Downloaded Markdown has no `Standard & Included` count.
- Sidebar still shows Standard & Included.

## Non-Goals

- Do not change workbook data.
- Do not change option rules or required-selection logic.
- Do not remove standard equipment from internal order data.
- Do not build the `Submit to Dealer` modal/Formidable hook in this pass.
