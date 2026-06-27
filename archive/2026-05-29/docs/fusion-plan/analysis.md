# Analysis

## Agreement
*11*
- All or most models say the Excel workbook should remain the source data, but the live configurator should run on cleaned, structured data rather than raw sheets.
- All or most models agree that every option and interior row needs a stable unique ID before any web implementation starts.
- All or most models recommend unpivoting the six variant columns into a normalized availability structure keyed by variant.
- All or most models agree the Detail/disclosure text must be tokenized into structured rules like requires, excludes, and includes; prose alone is not sufficient for app logic.
- All or most models treat the interior workbook as a separate configuration domain and recommend using its pre-flattened valid combinations rather than rebuilding interior logic from scratch.
- All or most models use the same base status model: standard is included at $0, available is selectable, and unavailable is hidden or disabled for the chosen variant.
- All or most models say Sections need explicit logic for mutual exclusivity and required selections, with validation before submission.
- All or most models calculate price from base variant price plus interior plus selected paid options, while excluding standard/included items and avoiding double counting.
- All or most models call out the same major workbook risks: missing IDs, untokenized rules, and overlap between packages/interior/main options that can create invalid builds or duplicate pricing.
- All or most models propose a phased rollout that starts with workbook cleanup and normalization before database/API/front-end work.
- All or most models include customer lead capture and a final build summary as part of the submission flow.

## Key Differences
*4*

### Where the configurator’s rule and pricing logic should run at runtime

- GPT-5.4
  - Use a normalized database plus a server-side rules resolver as the authoritative engine.
- Gemini 3.1 Pro Preview
  - Load JSON into the browser and do filtering/calculation locally; use the backend mainly to store the final submission.
- Claude Opus 4.7
  - Use static JSON plus a lightweight front-end state machine, with a serverless endpoint only for submission/admin tasks.
- Kimi K2.6
  - Use a relational database and API to serve filtered data, validate rules, and save submissions

### What should serve as the stable primary identifier for options

- GPT-5.4
  - Create synthetic internal IDs everywhere and keep RPO only as a display/search field, not the primary key.

- Gemini 3.1 Pro Preview
  - Use RPO if it is truly unique, otherwise derive a UID such as RPO plus variant group.

- Claude Opus 4.7
  - Use the RPO as the option_id where it exists, and create synthetic IDs only for exceptions.

- Kimi K2.6
  - Add UUID/serial IDs and treat RPO as a natural key, not the primary key.

### When interior should appear in the customer flow

- GPT-5.4
  - Select variant first, then handle interior as the next dedicated step before main options.

- Gemini 3.1 Pro Preview
  - Handle interior immediately after variant using a cascading seat/color filter before the main options grid.

- Claude Opus 4.7
  - Show standard equipment and some sections first, then do interior, then exterior/remaining options.

- Kimi K2.6
  - Place interior right after variant and before the main options selection step.

### Whether standard options are locked inclusions or replaceable defaults

- GPT-5.4
  - In single-select sections, standard should often behave as the default included choice that can be replaced by another available option.

- Gemini 3.1 Pro Preview
  - Standard is forced selected and shown as included at $0; replacement behavior is not emphasized.

- Claude Opus 4.7
  - Standard items are auto-added, locked, and generally kept out of selectable lists.

- Kimi K2.6
  - Standard items are rendered preselected and locked, although section logic may still auto-deselect them when another option in the same section is chosen.

## Partial Coverage
*5*

### They explicitly recommend a section registry/master table with required flags and selection types instead of inferring section behavior from the raw workbook.
- GPT-5.4
- Claude Opus 4.7
- Kimi K2.6

### They call for automated validation outputs that flag duplicate IDs, orphaned rule references, missing categories/sections, and other import errors.
- GPT-5.4
- Claude Opus 4.7
- Kimi K2.6

### They preserve the original disclosure text for display while using structured rule fields for logic, allowing unresolved text to remain visible without driving the engine.
- GPT-5.4
- Claude Opus 4.7
- Kimi K2.6

### They explicitly address versioning/history so model-year or workbook changes do not silently rewrite past builds or pricing.
- GPT-5.4
- Claude Opus 4.7

### They explicitly want server-side validation or pricing checks at submission time instead of trusting only the browser’s running total.
- GPT-5.4
- Claude Opus 4.7

## Unique Insights
*4*

### Store a frozen JSON snapshot plus a data version with each submitted build so later workbook edits cannot alter historical summaries or totals.
- GPT-5.4

### Treat destination freight as a separate pricing line item and consider gating the printable/PDF summary behind lead capture.
- Gemini 3.1 Pro Preview

### Add a dedicated standard-equipment review panel/step early in the wizard to explain what is already included and reduce confusion about missing options.
- Claude Opus 4.7

### Before coding, audit one real interior combination against the main options sheet to decide whether interior pricing is bundle-based or sum-of-parts.
- Kimi K2.6

## Blind Spots
*4*

1. None of the models adequately addressed privacy/security for collecting PII, including consent language, spam protection, retention rules, and access controls.
2. None adequately covered accessibility requirements for a public-facing configurator, such as keyboard navigation, screen-reader labels, contrast, and error messaging.
3. None fully handled legal/pricing disclosure needs like taxes/title/registration, quote-validity language, MSRP-vs-final-price labeling, and consistent treatment of fees.
4. None meaningfully addressed the content/asset side of a customer-facing builder, such as option images, swatches, preview media, and how those assets would be maintained alongside the workbook.
