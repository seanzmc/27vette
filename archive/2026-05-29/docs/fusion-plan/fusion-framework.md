# Practical plan to turn your Corvette Options workbook into a customer-facing online build form

## Short answer

The best approach is:

1. **Keep Excel as the authoring/source file**
2. **Do not use the raw workbook directly as the live configurator**
3. **Add IDs, helper sheets, and structured rules**
4. **Import the cleaned data into a normalized database**
5. **Run a shared rules/pricing engine in the browser for speed and on the server for final validation**
6. **Treat the interior sheet as its own configuration domain**
7. **Store each submitted build as a frozen snapshot with versioned pricing**

That gives you a configurator that is fast for customers, maintainable for you, and accurate enough to prevent invalid builds and bad pricing.

---

# 1) Recommended system design

## Best architecture

Use this flow:

```text
Excel workbook
  -> preprocessing/import script
  -> normalized database + versioned JSON payloads
  -> customer-facing web app
  -> submission storage + email/PDF + CRM/admin
```

## Recommended stack

A practical implementation:

- **Frontend:** Next.js / React
- **Backend:** Next.js API routes or small Node/FastAPI service
- **Database:** PostgreSQL (Supabase is a good fit)
- **Import/preprocessing:** Python or Node script
- **Email:** Postmark / Resend / SendGrid
- **Hosting:** Vercel + Supabase/Render/Railway

If you already live in Microsoft tools, Power Apps is possible, but for a public automotive configurator with dependencies and pricing rules, a small custom app is usually the cleaner long-term solution.

## Where the logic should run

**Use a hybrid model.**

### In the browser
For speed and good UX:
- load the selected model year / variant dataset
- update availability instantly as the customer clicks
- show running total, included items, disabled reasons, and required-section status

### On the server
For authority and safety:
- re-run the same rules at submission time
- re-calculate price
- reject invalid or tampered builds
- store final snapshot

**Recommendation:** implement the rules/pricing engine once in a shared code library, then use it both client-side and server-side.

That gives you the best of both worlds:
- fast configurator
- trustworthy submission pricing

---

# 2) What to change in the workbook before building anything

## Non-negotiable additions

You need stable IDs and machine-readable structure.

## Add these IDs

### Main options sheet
- `option_id` → internal synthetic ID like `OPT_0001`
- keep `RPO` as a display/search field, **not** as the primary key

### Interior sheet
- `interior_combo_id` → internal synthetic ID like `INT_0001`

### Master/helper sheets
- `variant_id`
- `category_id`
- `section_id`
- `rule_id`
- `data_release_id` or `model_year_release_id`

## Why not use RPO as the primary key?
Because RPOs are useful but not reliable enough to be your only identifier:
- some rows may be blank or duplicated
- the same RPO can behave differently by trim/body
- rules should never depend on row numbers or label text
- internal IDs give you stable references even when names change

---

# 3) Recommended workbook helper sheets

You should add helper sheets, not just extra columns.

## Required helper sheets

### `Variant_Master`
One row per buildable variant.

Columns:
- `variant_id`
- `model_year`
- `trim_level`
- `body_style`
- `display_name` (`2LT Coupe`)
- `base_price`
- `display_order`
- `active`

---

### `Category_Master`
Columns:
- `category_id`
- `category_name`
- `display_order`

---

### `Section_Master`
This is critical. Do not infer section behavior from raw sheet layout.

Columns:
- `section_id`
- `section_name`
- `category_id`
- `selection_mode`
- `is_required`
- `display_order`
- `standard_behavior`
- `none_allowed`
- `help_text`

Recommended `selection_mode` values:
- `single_select_required`
- `single_select_optional`
- `multi_select_optional`
- `multi_select_required`
- `display_only`

Recommended `standard_behavior` values:
- `locked_included`
- `replaceable_default`

This resolves one of the biggest ambiguities in your current workbook.

---

### `Section_Variant_Rules` (only if needed)
Use this if a section’s visibility/required status varies by variant.

Columns:
- `section_id`
- `variant_id`
- `is_visible`
- `is_required`
- `default_option_id` (optional)

---

### `Option_Master`
A cleaned version of the main options layout.

Columns:
- `option_id`
- `rpo`
- `option_name`
- `description`
- `detail_raw`
- `price`
- `category_id`
- `section_id`
- `selectable`
- `display_order`
- `source_domain` (`main` / `interior`)
- `active`

Keep `detail_raw` exactly as-is for customer display, even after you tokenize rules.

---

### `Option_Variant_Status`
This is the unpivoted version of the six wide variant columns.

Columns:
- `option_id`
- `variant_id`
- `status` (`standard`, `available`, `unavailable`)

Do **not** keep the live app logic tied to six separate spreadsheet columns.

---

### `Rule_Mapping`
This is where the prose in `Detail` becomes actual logic.

Columns:
- `rule_id`
- `source_type` (`option`, `interior_combo`)
- `source_id`
- `rule_type`
- `target_type` (`option`, `section`, `variant`)
- `target_id`
- `display_text`
- `priority`
- `notes`

Start with these rule types:
- `requires`
- `excludes`
- `includes`

Later, if needed:
- `forces_section_choice`
- `overrides_color`
- `replaces`
- `blocks_option`

---

### `Interior_Combo_Master`
Use your flattened interior data as the source of truth.

Columns:
- `interior_combo_id`
- `model_year`
- `variant_id` or trim/body eligibility
- `seat_type`
- `interior_color`
- `trim_material`
- `display_name`
- `price`
- `related_options_raw`
- `override_notes_raw`
- `display_order`
- `active`

---

### `Interior_Combo_Components`
Optional but strongly recommended.

Columns:
- `interior_combo_id`
- `option_id` or `component_label`
- `component_role` (`seat`, `trim`, `color`, `included_feature`)
- `display_order`

This makes summaries much cleaner.

---

### `Fees_Disclosures`
Needed for pricing clarity.

Columns:
- `fee_id`
- `model_year`
- `fee_type` (`destination_freight`, etc.)
- `amount`
- `applies_to_variant_id` or `all`
- `display_label`
- `active`

If freight is already inside your base price map, document that here so you do not double-count it.

---

### `Asset_Map`
For customer-facing content.

Columns:
- `asset_id`
- `asset_type` (`option`, `interior_combo`, `category`, `color_swatch`)
- `source_id`
- `image_url`
- `thumbnail_url`
- `swatch_hex`
- `alt_text`
- `display_order`

Even if v1 is mostly text-based, create this hook now.

---

### `Validation_Issues`
Generated by your import process.

Examples of flagged issues:
- duplicate `option_id`
- duplicate/ambiguous RPO
- missing section/category
- orphaned rule target
- invalid variant status
- multiple standards in a single-select section
- selectable option in `display_only` section
- unresolved disclosure text
- interior/main option overlap that may double-charge

---

# 4) Target database structure

A normalized relational model is the right fit.

## Core tables

### `data_releases`
Version every workbook import.

Columns:
- `data_release_id`
- `model_year`
- `source_file_name`
- `imported_at`
- `notes`
- `is_active`

This prevents silent rewrites of old builds.

---

### `variants`
- `variant_id`
- `data_release_id`
- `display_name`
- `trim_level`
- `body_style`
- `base_price`

---

### `categories`
- `category_id`
- `data_release_id`
- `name`
- `display_order`

---

### `sections`
- `section_id`
- `data_release_id`
- `category_id`
- `name`
- `selection_mode`
- `is_required`
- `standard_behavior`
- `display_order`

---

### `section_variant_rules`
- `section_id`
- `variant_id`
- `is_visible`
- `is_required`
- `default_option_id`

---

### `options`
- `option_id`
- `data_release_id`
- `rpo`
- `option_name`
- `description`
- `detail_raw`
- `price` (store in cents)
- `category_id`
- `section_id`
- `selectable`
- `source_domain`
- `display_order`

---

### `option_variant_status`
- `option_id`
- `variant_id`
- `status` (`standard`, `available`, `unavailable`)

---

### `option_rules`
- `rule_id`
- `data_release_id`
- `source_type`
- `source_id`
- `rule_type`
- `target_type`
- `target_id`
- `display_text`
- `priority`

---

### `interior_combos`
- `interior_combo_id`
- `data_release_id`
- `display_name`
- `variant_id` or eligibility mapping
- `seat_type`
- `interior_color`
- `trim_material`
- `price`
- `override_notes_raw`

---

### `interior_combo_components`
- `interior_combo_id`
- `component_role`
- `option_id` or display label
- `display_order`

---

### `fees`
- `fee_id`
- `data_release_id`
- `fee_type`
- `amount`
- `display_label`

---

### `assets`
- `asset_id`
- `asset_type`
- `source_id`
- `image_url`
- `swatch_hex`
- `alt_text`

---

### `builds`
- `build_id`
- `data_release_id`
- `variant_id`
- `interior_combo_id`
- customer fields
- `base_price`
- `fees_total`
- `options_total`
- `total_price`
- `snapshot_json`
- `created_at`
- `submitted_at`

---

### `build_selected_items`
- `build_id`
- `option_id`
- `selection_source` (`manual`, `standard`, `included`, `interior`)
- `price_applied`

The `snapshot_json` is important. It preserves the exact build summary, labels, and pricing at submission time even if the workbook changes later.

---

# 5) How to tokenize rules from the Detail column

## Keep the prose, but don’t run the app from prose

Your `Detail` text is valuable for customer display, but it is **not** reliable app logic.

### Example

Raw text:
> Requires Z51 Performance Package. Not available with visible carbon fiber roof.

Structured rules:
- source = this option
- `requires` → Z51 option row
- `excludes` → carbon roof option row

## Best practical approach

Use a **semi-manual tokenization workflow**:

1. Export all unique `Detail` values
2. Use name/RPO matching to suggest targets
3. Manually confirm each target
4. Write the confirmed mapping into `Rule_Mapping`
5. Keep any unresolved text visible as disclosure, but do not trust it for logic

This is slower than auto-parsing, but it is the difference between a reliable configurator and one that occasionally allows illegal builds.

## What to do with unresolved disclosures
If a rule is not yet tokenized:
- **still show the raw text in the UI**
- flag it in `Validation_Issues`
- treat it as a known gap until mapped

---

# 6) How to handle Standard vs Available vs Unavailable

Think of this in two layers.

## Layer 1: variant-level base status
For the selected variant, every option starts as:
- `standard`
- `available`
- `unavailable`

This comes directly from `option_variant_status`.

## Layer 2: effective runtime state
After the customer makes selections, that base state can change in practice:
- an `available` option may become blocked by an exclusion
- an `available` option may become required by another selection
- an option may become `included` through a package
- a `standard` item may remain locked or may be replaced, depending on the section rules

## Clear recommended behavior

| Status / state | Customer behavior | Price |
|---|---|---:|
| `standard` + `locked_included` | auto-selected, not removable | $0 |
| `standard` + `replaceable_default` | preselected, but can be swapped in its section | $0 unless replaced |
| `available` | selectable | option price |
| `unavailable` | hidden or disabled with reason | n/a |
| `included` by another option | shown as included, not separately selectable | $0 |

## Important position on “standard”
A standard item is **not automatically “locked forever.”**

For example, in a single-select section like wheels:
- one wheel may be standard for the variant
- it should appear as the default selected choice
- if the customer picks an upgrade wheel, the standard wheel is replaced

So the app should not treat every standard row as permanently locked.
That behavior must come from `Section_Master.standard_behavior`.

---

# 7) How to handle the interior configuration

## Recommendation: keep interior separate

Because your interior sheet is already flattened into valid combinations, **do not rebuild interior logic from scratch** in v1.

Treat interior as its own configuration domain.

## Best v1 approach

### Customer flow
1. Customer chooses variant
2. App shows only interior combos valid for that variant
3. Customer selects seat/color/trim using guided filters
4. That resolves to one `interior_combo_id`
5. The combo contributes:
   - one price
   - display components
   - any override/exclusion effects

## UI recommendation
Use a guided filter, not a giant combo list:
- Step A: seat type
- Step B: interior color
- optional Step C: trim/material if needed
- final result = one interior combo row

That uses your flattened data without exposing the complexity.

## How interior should interact with main options
Use interior as the source of truth for interior selections.

### Recommended rule
If an item is represented by the interior combo:
- **do not also present it as an independent main-option control**
- mark overlapping main rows as `source_domain = interior` or `selectable = false`

### If interior affects main options
Use rules with `source_type = interior_combo`, for example:
- interior combo excludes a belt color
- interior combo triggers an exterior color override
- interior combo blocks a trim piece

## Critical audit before coding
Pick one real interior combination and compare it to the main options sheet.

Example:
- `2LT Coupe`
- one actual seat/color combo

Then answer this:
- Is interior priced as a **bundle**
- or as **sum of the included component RPOs**

**Recommendation:** make the interior combo the pricing authority in v1.
If the combo includes seat/trim/color components, show them for summary, but charge the combo price once. That avoids double-counting.

---

# 8) Recommended form flow

## Step 1: Select model variant
Customer chooses:
- 1LT Coupe
- 2LT Coupe
- 3LT Coupe
- 1LT Convertible
- 2LT Convertible
- 3LT Convertible

On selection:
- load base price
- load applicable sections
- load standard equipment
- load eligible interior combos
- load fees such as freight if separately modeled

---

## Step 2: Show a standard-equipment review panel
This is worth adding early.

Why:
- reduces confusion about “missing” features
- reinforces value of the chosen trim
- answers “what’s already included?”

Show:
- standard equipment for this variant
- grouped by category
- collapsible if long

---

## Step 3: Interior configuration
Use seat/color guided selection to resolve one interior combo.

On select:
- add combo price
- show included interior components
- apply override rules
- update running total

---

## Step 4: Main options by category and section
Display by `Category` for presentation, and enforce logic by `Section`.

### UI control mapping
- `single_select_required` → radio buttons/cards
- `single_select_optional` → radio buttons/cards + “None”
- `multi_select_optional` → checkboxes
- `display_only` → no control, summary only

### On each option card, show:
- option name + RPO
- price
- short description
- raw detail/disclosure text
- tokenized “Includes …” items inline if mapped
- disabled reason if blocked

### Conflict behavior
On selection:
- if it **includes** other items → auto-add them as included
- if it **requires** another option and that option is available → prompt to add it
- if it **requires** something unavailable on this variant → block and explain
- if it **excludes** a currently selected option → prompt user to remove the conflicting item or cancel

The engine must work **bidirectionally** so sequence doesn’t matter:
- selecting A after B should be handled the same as B after A

---

## Step 5: Review build
Show a full summary:
- variant
- base MSRP
- destination/freight if separate
- interior configuration
- selected options
- included items from packages/options
- standard equipment
- total MSRP estimate

Use a sticky running total during the build, then a clean full review screen here.

---

## Step 6: Customer information
Collect:
- first name
- last name
- address
- phone
- email

Recommended additional fields:
- preferred contact method
- preferred dealership/store location
- comments

## Gating recommendation
Let customers review their build live, but require contact info before:
- final submission
- emailed summary
- printable/PDF build sheet

That usually improves lead capture without hurting usability.

---

## Step 7: Submit
Server-side:
- re-run validation
- re-run pricing
- generate final snapshot
- store build
- email summary to sales team
- optionally email the customer a copy
- return confirmation with build ID

---

# 9) Pricing flow

## Recommended formula

```text
Total MSRP estimate =
  base vehicle price
+ destination freight / fixed fees you explicitly model
+ interior combo price
+ selected paid options
```

### Do not add:
- standard items
- items included by another selected option/package
- interior component rows if the combo already carries the price

## Important pricing rules

### Base price
Comes from `Variant_Master`.

### Standard items
- included in base price
- shown at $0 / Included

### Replaceable standard choice
If a standard option is replaced in a single-select section:
- remove the standard item from the effective selection
- charge only the selected upgrade option price

### Package includes
If a parent option includes child options:
- show child items nested under the parent in summary
- do not price the children separately

### Interior combo
Best v1:
- charge the combo once
- show components as informational/included items

### Freight / fees
Add destination freight as a separate line **only if it is not already inside your base price map**.
Document that decision once and keep it consistent.

### Taxes/title/registration
Usually **do not** include these in the configurator total unless you are truly calculating by state/jurisdiction.
Label the result as:
- **Estimated MSRP**
- or **Estimated Build Total Before Taxes and Registration**

---

# 10) Validation rules

## Build validation
Before submission:
- variant selected
- required interior selected
- all required visible sections satisfied
- no conflicting options
- all requires satisfied
- no unavailable items selected
- no duplicate billable lines
- price recalculated successfully

## Section validation
- required only if visible/applicable to the variant
- if a required section has a standard default already selected, mark it satisfied
- if a section becomes hidden due to a rule, remove validation for it

## Customer validation
- valid email format
- valid phone format
- required address fields completed
- consent acknowledgment if you will contact them

## Import validation
Your import process should flag:
- duplicate IDs
- missing required fields
- invalid statuses
- orphaned rule targets
- missing section/category mappings
- inconsistent display order
- unresolved detail text
- multiple standards in single-select sections
- interior/main overlap that can double-charge

---

# 11) Build summary flow

## Customer-facing summary should include

### Vehicle
- model year
- trim/body style
- base MSRP

### Interior
- selected interior combo
- interior price
- included seat/trim/color details

### Selected options
Grouped by category:
- option name
- RPO
- price
- included child items underneath marked `Included`

### Standard equipment
- collapsible list for selected variant
- do not show replaced standard items as still active

### Pricing
- base vehicle
- freight/fees if applicable
- interior
- options subtotal
- total MSRP estimate
- note that tax/title/registration are extra unless modeled

### Customer info
- name
- address
- phone
- email

### Metadata
- build ID
- timestamp
- data release / model year version

## Store a frozen snapshot
Every submitted build should save:
- selected IDs
- display labels at time of submission
- pricing at time of submission
- disclosures shown at time of submission
- total
- data release version

This prevents later workbook updates from changing historical builds.

---

# 12) Biggest risks in your current workbook

## 1. Untokenized disclosure text
This is the biggest issue.
Until `Requires`, `Includes`, and `Not available with` are mapped to actual IDs, the configurator cannot reliably enforce rules.

## 2. No stable unique IDs
Without internal IDs:
- rules will be fragile
- imports will break when rows move
- updates will be hard to manage

## 3. Section behavior is underdefined
You have `Section`, but the app also needs:
- single vs multi select
- required vs optional
- whether standard is locked or replaceable
- whether “None” is allowed

## 4. Interior and main options may overlap
This can cause:
- duplicate display
- duplicate pricing
- conflicting logic

## 5. Package/include overlap
If a package includes child options that are also sold standalone, you need dedupe logic or you will double-charge.

## 6. Inconsistent naming / orphan references
Rule mapping will fail if names, RPO usage, or section labels are inconsistent.

## 7. No versioning/history
If you update prices later, old customer builds should not silently change.

## 8. Freight/tax/legal labeling may be unclear
If you don’t explicitly define what is included in total, customer trust drops fast.

## 9. Public-form operational issues
A customer-facing tool also introduces:
- PII risk
- spam risk
- accessibility obligations
- content/asset maintenance

---

# 13) Privacy, security, accessibility, legal, and content requirements

These are easy to overlook, but they matter on a public-facing build form.

## Privacy and security
Because you are collecting name, address, phone, and email:

### Minimum requirements
- HTTPS only
- role-based admin access to submissions
- encrypt data at rest where possible
- limit who can export submissions
- audit who can see leads
- retention policy for old leads
- privacy policy link on the form
- contact-consent language near submit
- separate marketing opt-in if applicable

### Anti-spam protection
Add:
- honeypot field
- rate limiting
- CAPTCHA/hCaptcha/reCAPTCHA on submission
- server-side validation for all fields

Do not collect anything you do not need.

---

## Accessibility
Build to at least **WCAG 2.2 AA** expectations.

### Must-haves
- keyboard navigation through all steps
- proper labels for all form controls
- screen-reader-friendly error messages
- focus management after validation errors
- no color-only indicators for availability
- sufficient contrast
- accessible swatches with text labels
- large touch targets on mobile

This is especially important if you use visual option cards and color swatches.

---

## Legal/pricing disclosures
Show clear labels such as:
- “Estimated MSRP”
- “Destination freight included” or “Destination freight added separately”
- “Taxes, title, registration, and dealer fees not included”
- “Availability and pricing subject to change”
- “Images may not reflect exact configuration”

Also keep raw option disclosure text visible where relevant.
Do not hide important compatibility or availability disclaimers behind logic only.

---

## Content and assets
A customer-facing configurator is much better with images and swatches.

### Practical recommendation
Add an `Asset_Map` now, even if v1 is mostly text:
- option images
- interior swatches
- seat photos
- category hero images
- color swatches
- alt text

If you skip this now, you can still launch text-first, but the schema should already support it.

---

# 14) Phased implementation plan

## Phase 0 — Lock the business rules before coding
**Goal:** resolve pricing and ownership decisions that can break the app later.

Tasks:
- decide whether base price includes freight
- decide whether interior pricing is bundle-based or component-based
- audit one real interior combo against main-option pricing
- decide which main rows are interior-owned and should not be customer-selectable
- define your disclaimer language

Deliverable:
- one-page rules-of-record document

---

## Phase 1 — Workbook hardening
**Goal:** make the workbook importable.

Tasks:
- add `option_id` and `interior_combo_id`
- create `Variant_Master`
- create `Category_Master`
- create `Section_Master`
- define `selection_mode`, `is_required`, `standard_behavior`
- add `display_order`
- mark `source_domain`
- add `model_year` / `data_release_id`

Deliverable:
- cleaned workbook with IDs and master sheets

---

## Phase 2 — Normalize and tokenize rules
**Goal:** produce machine-readable build logic.

Tasks:
- unpivot the 6 variant columns into `Option_Variant_Status`
- create `Rule_Mapping`
- map `requires`, `excludes`, `includes`
- preserve `detail_raw` for display
- generate `Validation_Issues`
- resolve orphan references and duplicates

Deliverable:
- normalized CSV/JSON export set
- issue report
- resolved core rule library

---

## Phase 3 — Interior model setup
**Goal:** isolate interior logic cleanly.

Tasks:
- create `Interior_Combo_Master`
- create `Interior_Combo_Components`
- define interior eligibility by variant
- map color overrides/exclusions
- remove duplicate interior controls from main options UI

Deliverable:
- clean interior dataset with pricing authority clearly defined

---

## Phase 4 — Database and import pipeline
**Goal:** turn workbook data into app-ready data.

Tasks:
- create database schema
- write import script
- validate every import
- create `data_releases`
- store assets/fees/disclosures
- publish import logs

Deliverable:
- repeatable import pipeline
- seeded staging database
- versioned releases

---

## Phase 5 — Rules engine and pricing engine
**Goal:** guarantee valid builds and correct totals.

Tasks:
- build shared resolver
- implement:
  - variant filtering
  - standard/default selection
  - section mutual exclusivity
  - required section validation
  - includes/requires/excludes
  - interior overrides
  - pricing dedupe
- write test cases for known builds and known illegal combinations

Deliverable:
- tested rules engine
- tested pricing engine

---

## Phase 6 — Front-end configurator
**Goal:** customer-facing builder.

Tasks:
- variant selector
- standard-equipment panel
- interior guided selection
- category/section option UI
- running total sidebar
- review screen
- mobile-friendly layout
- accessibility pass

Deliverable:
- working staging configurator

---

## Phase 7 — Submission flow and compliance
**Goal:** turn the configurator into a lead-capture tool.

Tasks:
- customer info form
- consent/privacy text
- spam protection
- server-side validation
- build summary email
- PDF or printable summary
- admin lead view
- optional CRM integration

Deliverable:
- end-to-end submission flow with stored leads

---

## Phase 8 — QA, launch, and maintenance loop
**Goal:** go live without surprises.

Tasks:
- spot-check builds against workbook and official ordering guide
- test each variant
- test required sections and conflict flows
- test mobile usability
- test accessibility
- soft launch
- document the update process:
  - edit workbook
  - run import
  - review validation
  - publish new data release

Deliverable:
- production launch
- documented maintenance process

---

# 15) Immediate next steps I would do first

If you want the shortest path to a real build form, do these first:

1. **Add internal IDs** to every option and interior combo
2. **Create `Section_Master`** and explicitly define selection modes and required sections
3. **Unpivot the six variant columns** into long format
4. **Start `Rule_Mapping`** for `requires / excludes / includes`
5. **Audit one real interior combo** against the main sheet and decide pricing authority
6. **Identify interior-owned rows** in the main options sheet to prevent duplicate display/pricing
7. **Create a validation report** for duplicates, missing mappings, and orphan references
8. **Choose a versioning strategy** (`data_release_id`)
9. **Define freight/tax disclaimer treatment**
10. **Build the import pipeline before building the UI**

---

# Bottom-line recommendation

The right implementation is:

- **Excel remains the editing tool**
- **A preprocessing step converts it into structured data**
- **A normalized database stores options, sections, variants, rules, interiors, fees, and assets**
- **A shared rules engine powers a fast front-end and authoritative server-side validation**
- **Interior is handled as a separate, prevalidated combo selector**
- **Each submitted build is saved as a frozen, versioned snapshot**

If you want, the next useful step is to turn this into a **concrete workbook spec** with:
- exact sheet names
- exact column names
- sample rows
- a sample `Rule_Mapping` format
- and a sample JSON payload for the live form.
