# Coverage & Quality Audit: `form-app/styles.css`

An exhaustive coverage and structural audit of `form-app/styles.css` (2,891 lines, 411 rule blocks) cross-referenced against `form-app/index.html` and `form-app/app.js`.

A second pass on 2026-08-19 completed the first run after it hit the tool-iteration budget. Sections 1–7 are the original diagnosis. Sections 8–13 are new, verified findings that the first pass missed.

A third pass on 2026-08-19 corrected stale line references and two miscounts in §1–§5 and §8 after review. No finding was withdrawn; the diagnosis is unchanged. Every line number below was re-derived against `form-app/styles.css` at `3ce3cae` (2,891 lines). Line numbers are provenance, not edit addresses — re-grep by selector before editing.

Adoption contract: `docs/css-cleanup-adoption-spec.md`. That file owns step order, scope, and what may change HTML/JS. This audit stays the diagnosis.

---

## 1. Executive Summary & File Metrics

| Metric | Measured Value | Notes |
| --- | --- | --- |
| Total Lines | 2,891 lines | Including comments and whitespace |
| Total CSS Rule Blocks | 411 | 297 base rules + 114 media query rules |
| Media Queries | 7 blocks | Viewport breakpoints: 1400px, 1121px, 1120px, 887px/761px, 760px (2x), reduced-motion |
| Unique Class Selectors | 162 | Analyzed against DOM and JS template literals |
| Dead / Orphan Selectors | 8 classes (16 rules) | 0 DOM or JS consumers |
| Redundant Property Declarations | 24+ instances | Base properties re-declared with identical values in `@media` |
| High-Priority Value Conflicts | 1 critical (`.auto-reason`) | Direct property collision / overwrite |
| Font Weight Spectrum | 8 numeric weights + `inherit` | 400, 600, 650, 700, 750, 800, 850, 900, plus `font-weight: inherit` |

---

## 2. Priority Conflicts & Specificity Bugs

### Critical: `.auto-reason` Color Conflict

- **Location:** Lines 1446–1451 (`color` at 1448) vs Lines 1557–1559
- **Issue:**

```css
/* Lines 1446-1451; color at 1448 */
.disabled-reason,
.auto-reason {
  color: var(--warn); /* Sets warning color on auto-reason */
  font-size: 12px;
  font-weight: 750;
}

...

/* Line 1557 */
.auto-reason {
  color: var(--ok);   /* Overwrites color to ok */
}
```

- **Impact:** `.auto-reason` inherits `--warn` temporarily before being overridden 111 lines later. If selector specificity changes or rules are reordered, auto-added options will render in amber/warning instead of green/ok.

### Media Query Fragmentation (`max-width: 760px`)

- **Location:** Lines 711–729 and Lines 2378–2880
- **Issue:** `@media (max-width: 760px)` is split into two disjoint sections:
  1. Lines 711–729: Exterior paint vehicle-stage & swatch grid rules.
  2. Lines 2378–2880: Main responsive mobile layout (502 lines).
- **Impact:** Fragmented maintenance surface and unnecessary parse/cascade overhead.

### Duplicate Selectors Inside the Same Media Query

In `@media (max-width: 760px)` (Lines 2378–2880), several selectors appear twice. Two are true duplicate pairs; the third is a redundant re-declaration against a grouped selector and is not merged the same way:

1. `.choice-panel`: Line 2625 (`order: 2; min-width: 0;`) and Line 2779 (`padding: 16px;`).
2. `.vehicle-setup-next-action`: Line 2682 (`align-items: stretch; flex-direction: column;`) and Line 2855 (`display: none;`).
3. `.setup-choice-grid`: **not a duplicate pair.** Lines 2630–2634 are the *grouped* selector
   `.setup-choice-grid, .trim-setup-group .setup-choice-grid` carrying `grid-template-columns: 1fr;`
   and `min-width: 0;`. Line 2691 is the bare `.setup-choice-grid` carrying only
   `grid-template-columns: 1fr;`, which the grouped block already sets. The bare block is a
   redundant re-declaration: delete 2691 and leave 2630–2634 intact. Merging the two “keeping the
   later values” would drop `min-width: 0` and the `.trim-setup-group` scoping.

---

## 3. Dead & Unused Selectors (Zero Consumers)

Cross-referencing `index.html` and `app.js` identified 8 completely dead class families (16 rules across the stylesheet):

| Selector | Line Numbers | Context / Why It's Dead |
| --- | --- | --- |
| `.model-picker`, `.model-picker select` | 189, 199 | Retired legacy model picker dropdown. Replaced by step-rail navigation and vehicle-setup cards. |
| `.summary-drawer-icon` | 441 | Unused icon selector; summary drawer header and buttons use SVG or text labels. |
| `.vehicle-setup-intro` (+ `h3`, `.eyebrow`, `p`) | 736–751, 2687 | Retired container class. Replaced by `.vehicle-setup-group-heading`. |
| `.choice-relation-eyebrow` | 1103, 1109 | `renderChoiceRelationGroup` in `app.js` only emits `.choice-relation-title` and `.choice-relation-note`. |
| `.choice-relation-count` | 1133 | No count badge is generated in the relational options group DOM. |
| `.choice-note` | 1433, 2818, 2828 | Relational notes and disclosures now render via badge tooltips or description fields; class is never attached. |
| `.customer-card` | 1653 | `renderCustomerForm` produces `.customer-step-form` and `.customer-field-grid`; `.customer-card` is unused. |
| `.tooltip-tail` | 2060 | Floating tooltips use `.tooltip-panel`, `.tooltip-content`, `.tooltip-lead`, and `.tooltip-list`. |

---

## 4. Redundant Rules & Cascading Bloat

Dozens of rules inside responsive media queries repeat properties that already match the default base stylesheet:

**Redundant Declarations in Media Queries:**

1. **`.summary-panel`** (Line 2276 in `@media (max-width: 1120px)`):
   Repeats 9 properties identical to base lines 1567–1581 (`position: fixed`, `inset: 0 0 0 auto`, `z-index: 30`, `width: min(88vw, 380px)`, `max-width: 380px`, `border-left: 1px solid var(--hairline)`, `overflow-y: auto`, `transform: translateX(100%)`, `transition: transform 180ms ease`). The same block also sets `border: 0` and `padding: 16px`, which are **not** redundant — base sets no `border` and uses `padding: 14px 12px`. Only the 9 identical properties are removable.
2. **`.mobile-drawer-backdrop:not([hidden])`**:
   Declared **4** times, three of them identical. Base Line 1604 (`position: fixed; inset: 0; z-index: 20; display: block; background: rgba(0, 0, 0, 0.55)`) is repeated verbatim at Line 2307 (`@media (max-width: 1120px)`) and Line 2750 (`@media (max-width: 760px)`). The fourth, Line 2222 inside `@media (min-width: 1121px)`, is `display: none` — a live override that hides the backdrop in the docked desktop layout. It is not a copy and must not be deleted with them.
3. **Card Reordering (`order: 1..4`)**:
   `#requirementsCard` (`order: 2`), `#selectedRposCard` (`order: 3`), `#autoAddedCard` (`order: 4`), and `#summaryOverviewCard` (`order: 1`) are defined identically in base (Lines 1941–1955) and re-declared identically in `@media (max-width: 760px)` (Lines 2758–2771).
4. **`.topbar`**:
   `align-items: center` is re-declared in 3 separate `@media` queries without variation — Lines 2233 (`max-width: 1120px`), 2320 (`min-width: 761px) and (max-width: 887px`), and 2397 (`max-width: 760px`) — against base Line 86.
5. **`.step-link`** (Line 2715):
   Redeclares `width: 100%`, `grid-template-columns: 26px 1fr`, and `text-align: left`.

---

## 5. Token Inconsistencies & Hardcoding

### Font Weight Clutter

The stylesheet uses 8 numeric font weights (400, 600, 650, 700, 750, 800, 850, 900), plus `font-weight: inherit`. Standard variable font scaling for the UI should be consolidated to 4 semantic tokens:

- **Regular:** 400
- **Semi-bold / Medium:** 600
- **Bold:** 700
- **Heavy / Extra-bold:** 800 (or 850)

### Hardcoded Palette Values

Rather than referencing `:root` CSS variables, several arbitrary hex and rgba values are scattered in component blocks:

- `#cfd3d6` (used 4 times across icon buttons, step rail, stage pills)
- `#1a1d1f`, `#101214`, `#0f1112`, `#172026` (hardcoded dark backgrounds)
- `#f0c07a` (hardcoded amber text)
- `rgba(232, 161, 60, 0.4)` / `rgba(53, 184, 93, 0.4)` (hardcoded warning/ok borders)

---

## 6. Modern CSS Modernization Opportunities

1. **Native CSS Nesting:**
   - Deeply nested component trees (e.g., `#stepContent[data-active-step="paint"]`, `.choice-card`, `.vehicle-setup-panel`, `.summary-panel`, `.info-tooltip`) can be nested directly, cutting selector repetition by ~35%.
2. **Modern Color Functions (`color-mix`):**
   - Replace manual `rgba(255, 255, 255, 0.07)` and hardcoded amber/green alpha variants with `color-mix(in srgb, var(--accent) 20%, transparent)` and `color-mix(in srgb, var(--ok) 16%, transparent)`.
3. **Container Queries (`@container`):**
   - Use container queries on `.choice-panel` and `.vehicle-stage` so card grid columns (`repeat(auto-fill, minmax(230px, 1fr))`) and visualizer scaling adapt dynamically to available panel width rather than strict global window breakpoints (`max-width: 760px`).
4. **Logical Properties:**
   - Migrate `margin-left` / `margin-right` / `padding-left` / `padding-right` to `margin-inline` / `padding-inline` and `inset-inline` for cleaner bidirectional and responsive layout definitions.
5. **Subgrid for Form / Summary Alignment:**
   - `.summary-rpo-row` (`grid-template-columns: minmax(42px, auto) minmax(0, 1fr) auto`) and `.customer-field-grid` can leverage CSS Subgrid for perfect horizontal alignment across nested items.

---

## 7. Recommended Cleanup Checklist

- [ ] **Step 1: Remove Dead Selectors** — Strip the 8 unreferenced selector groups (saves ~80 lines).
- [ ] **Step 2: Fix Priority & Collision Bugs** — Clean up `.auto-reason` color override and remove duplicate selector blocks within `@media (max-width: 760px)`.
- [ ] **Step 3: Consolidate Media Queries** — Unify the two `@media (max-width: 760px)` blocks into a single cohesive mobile layout section.
- [ ] **Step 4: Deduplicate Inherited Properties** — Remove the 24+ identical re-declarations from responsive queries where base rules already apply.
- [ ] **Step 5: Normalize Font Weights & Palette Tokens** — Map intermediate weights (650, 750, 850) to standardized typography tokens and replace scattered hex codes with `:root` CSS variables.
- [ ] **Step 6: Adopt CSS Nesting** — Convert component blocks into nested structures to reduce bundle size and enhance maintainability.

**Constraint added by the second pass:** Step 6 is not safe against the current CSS-text test contract. See §8. Do not nest until that contract is migrated, or defer nesting.

---

## 8. Test-Asserted CSS Contract (missed by the first pass)

`form-app/styles.css` is hand-authored source, not a generated artifact. Two runtime suites read it as raw text and regex-assert against it:

- `tests/stingray-form-regression.test.mjs` — `stylesSource` at line 19; helpers `cssOrderFor()` (line 55, 5 call sites) and `cssBlock()` (line 61, 16 call sites). **89** `assert.*` calls take CSS text as their first argument (`stylesSource`, a media-query slice, `cssBlock(...)`, or `cssOrderFor(...)`) — measured, not estimated.
- `tests/multi-model-runtime-switching.test.mjs` — lines 856–857, two `.choice-relationship-badge` assertions.
- `tests/validation_catalog.json` line 585 lists the file as a styling-lane read input.

Three properties of those assertions constrain any cleanup:

1. **Flat-block regexes.** `cssBlock()` matches `(?:^|\n)<selector>\s*\{[\s\S]*?\}` — a non-greedy match to the first `}`. Native CSS nesting (audit §6 item 1 / checklist Step 6) makes that match stop early and silently truncate. Nesting is unsafe for any selector those tests touch until the helper is replaced with a parsed-CSS walker.
2. **Property-order-sensitive regexes.** Example: `.vehicle-setup-chip` is asserted as `justify-self` → `width` → `max-width` → `min-width` in written order. Reordering declarations during dedupe breaks the suite.
3. **Media-block slicing by source position.** The Stingray suite slices by `indexOf("@media (max-width: 1120px)")`, then the 761–887 block, then the *second* `max-width: 760px` (skipping the earlier paint-scoped 760px block), then reduced-motion. Current source order, verified: 1400 (701), 760 (711), 1121 (2198), 1120 (2227), 761–887 (2316), 760 (2378), reduced-motion (2882). Merging the two 760px blocks *backward* into line 711 would invert cascade against the 1120 / 887 blocks and break the slice. If they are consolidated, merge the paint rules *forward* into the 2378 block.

Negative DOM assertions already pin three of the dead CSS classes so they cannot return in HTML/JS: `.summary-drawer-icon`, `.vehicle-setup-intro`, `.choice-relation-count`. Those stay even if the CSS rules are deleted.

---

## 9. Unused Tokens and No-op Rules

### Unused `:root` tokens

| Token | Evidence | Notes |
| --- | --- | --- |
| `--shell-gap` | Defined line 38; zero `var(--shell-gap)` consumers | `tests/stingray-form-regression.test.mjs:804` already asserts `doesNotMatch` for `gap: var(--shell-gap)`. The token is leftover from a retired desk-margin shell. |
| `--choice-hover` | Defined line 29 as `#181d20`; zero `var(--choice-hover)` consumers | `--choice-hover-border` and `--choice-hover-shadow` are live. Choice-card hover restates `background: var(--choice-bg)` (line 1276), so the hover fill token was never wired. |

`--choice-bg` (`#14181b`) is also byte-identical to `--panel-strong`. Not unused, but the two tokens do not encode different colors.

### Empty / no-op rules

- **`.vehicle-setup-chip[data-setup-chip-state="complete"] strong::after`** (lines 850–852) sets only `content: ""` with no size, icon, or positioning. Sibling rule 854–857 already paints the complete state on `span`. Dead leftover from a checkmark that was never finished.
- **`.choice-card.auto`** (1297–1301) restates `border-color: var(--line)` and `background: var(--choice-bg)`, both already true on `.choice-card`. Only `outline-color: var(--ok)` is new.
- **`.choice-card:hover`** (1274–1278) restates `background: var(--choice-bg)` (same as the resting card). The live hover change is border + hard offset shadow.
- **`.summary-card:hover`** (1621–1624) restates `background: var(--panel-strong)` (same as the resting card) and only changes `border-color`. The `box-shadow` transition on `.summary-card` never fires because hover never sets a shadow.

---

## 10. Inverse Coverage: Live Classes With No CSS

The first pass listed CSS with no emitters. The reverse is also true — `index.html` / `app.js` emit class names that `styles.css` never styles:

| Class | Emitter | Impact |
| --- | --- | --- |
| `.has-media` | `app.js` pushes it on every media card (1993, 2041, 2136, 2291) | Dead hook. Hover-swap styling keys off `.has-hover-media` instead. Either delete the push or give it a rule. |
| `.positive` | Complete-requirements row: `<li class="empty positive">` (`app.js:2804`) | The row inherits italic muted `.empty` only. There is no success treatment for “all required selections are complete.” |
| `.dealer-turnstile` | `index.html:151` | Unstyled Cloudflare Turnstile mount. Layout/spacing is whatever the widget injects. |
| `.summary-action-button` | `index.html:54` on the mid-width Build Summary control | No rule. Harmless extra class. |
| `.structured` | `app.js:305` on `.tooltip-content.structured` | No rule. Tooltip layout comes from `.tooltip-content` / `.tooltip-list` alone. |
| `.body-setup-group` | `app.js:2391` | Sibling `.trim-setup-group` and `.model-setup-group` have rules; body-style setup has none. Either intentional (inherit panel defaults) or an unfinished third variant. |

JS also sets `data-has-next` on `#mobileProgress` (`app.js:1945`) but CSS only consumes `data-has-previous`. Not a bug today — `#mobileNextStep` is `display: none` at 760px — but the hook is one-sided.

---

## 11. Cascade, Stacking, and Interaction Bugs

### Unscoped `button` plus a `filter: none` tax

The element selector `button` (203–217) applies accent fill, uppercase, 800 weight, 12.5px type, and `box-shadow: 0 8px 24px var(--accent-glow)` to **every** button, including drawers, chips, cards, toast dismiss, and modal close. Downstream variants then spend 11 `filter: none` declarations undoing `button:hover { filter: brightness(1.08) }`. This is the largest single source of override bloat in the file.

A layered control model (`button` reset → `.btn` / `.btn-primary` → variants) would delete most of those resets. It is also the reason `.choice-card`, `.step-link`, `.vehicle-setup-chip`, and `.toast-dismiss` must each restate `text-transform: none`, `letter-spacing: 0`, `box-shadow: none`, and `font-weight`.

There is no `button:focus-visible` rule. Browser-default outline is the only focus ring on primary actions, Reset/Download icon buttons, `.ghost-button`, `.step-link`, and `.toast-dismiss`. Designed `:focus-visible` exists on choice cards, chips, the brand link, form fields, tooltips, modal close, and the two mobile header controls only.

### Incomplete `prefers-reduced-motion`

The reduce block (2882–2891) clears transitions on `button`, `.step-link`, `.choice-card`, `.summary-card`, `.info-icon`, `.tooltip-panel`. Live transitions it does **not** disable:

- `.interior-group` (1164)
- `.choice-media.has-hover-media img` (opacity 280ms, plus `will-change: opacity` at 1347)
- `.summary-panel` drawer slide (1580, 180ms)
- `.step-rail` drawer slide (line 2706, 180ms)

Hover-swap images and both mobile drawers still animate when the user asked for reduced motion.

### Z-index scale is ad hoc

| Layer | Value | Selector |
| --- | --- | --- |
| Paint sticky stage | 6 | `#stepContent[data-active-step="paint"] .vehicle-stage` |
| Mobile sticky footer | 5 | `.step-footer` at 760px |
| Docked summary (wide) | 1 | `.summary-panel` inside `min-width: 1121px` |
| Drawer / summary overlay | 30 | `.summary-panel`, `.step-rail` |
| Backdrop | 20 | `.mobile-drawer-backdrop`, `.modal-backdrop` |
| Toast | 60 | `.toast-region` |
| Tooltip (inline) | 80 / 90 | `.info-tooltip.is-open` / `.tooltip-panel` |
| Tooltip (viewport-floated) | 120 | `.tooltip-panel[data-floating="viewport"]` |

`.modal-backdrop` and the drawer backdrop share `z-index: 20`. A floated tooltip at 120 paints over the dealer-submit modal. Toasts at 60 also paint over that modal. There are no named stacking tokens (`--z-toast`, `--z-modal`, `--z-tooltip`).

### Duplicated carbon texture

The 6×6 checker (`linear-gradient(45deg, #181c1f …)` + `background-size: 6px 6px`) is copied verbatim on `body` (49–54) and again on the sticky paint stage (663–668) so cards can scroll underneath. It is not a token or a utility class. Any texture tweak must be made twice or the paint step desyncs from the page.

### Two visually-hidden recipes

`.reset-label, .download-label` (278–286) and `.sr-only` (later in the file) both clip text with `clip: rect(...)`. The icon-button version omits `padding`, `margin: -1px`, and `border: 0`. One shared `.sr-only` (or a `visually-hidden` utility) is enough; the older `clip: rect` form can move to `clip-path: inset(50%)`.

---

## 12. Additional Streamline / Modern-CSS Gaps

These sit beside §6; they were not in the first pass.

1. **Inter is named and never loaded.** `body` asks for `Inter, ui-sans-serif, …` (`styles.css:56`). `index.html` has no Google Fonts link, no `@font-face`, and no local Inter files. Production falls through to the system stack. Either load Inter or drop the name so the intended face is honest.
2. **`will-change: opacity` is always on** for `.choice-media.has-hover-media img`. That promotes a layer per media card for the life of the page. Prefer setting it on `:hover` / `:focus-visible` only, or drop it — `opacity` compositing does not need a permanent hint.
3. **`* { box-sizing: border-box }` does not cover pseudo-elements.** `::before` / `::after` (disclosure carets, the empty complete-chip after) inherit content-box unless listed. Use `*, *::before, *::after`.
4. **Disclosure markers are WebKit-only.** Three `::-webkit-details-marker { display: none }` rules have no `::marker` companion, so non-WebKit engines may still show the native triangle next to the custom ▸/▾. None of the three is a bare `summary::` selector, so each companion must mirror its own selector: `.vehicle-setup-equipment-disclosure summary` (988), `.interior-group-header` (1189), and `.standard-equipment-rollup > summary.standard-equipment-summary` (2165). `.interior-group-header` is rendered as a `<div>` at `app.js:2110` and as a `<summary>` at `app.js:2118`; only the `<summary>` instance draws a marker.
5. **Mobile line-clamp is prefixed only.** The 760px block uses `display: -webkit-box` + `-webkit-line-clamp: 3` (2822–2825, 2831) and never sets standard `line-clamp`. Add the unprefixed property beside it.
6. **Hardcoded white-alpha scale is the real palette bloat.** Unique `rgba(255,255,255,α)` stops already in the file: 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.24, 0.3, 0.32. That is 15 hairline/fill opacities on top of `--hairline` / `--hairline-strong` / `--control-*` / `--ghost-*`. Collapse to 4–5 surface tokens (`--surface-1` … `--line-strong`) before adding more component hexes.
7. **21 distinct `font-size` values**, including 9px, 10px, 11.5px, 12.5px. Pair this with the 8-weight problem in §5. A type scale (`--fs-2xs` … `--fs-xl`) is the higher-leverage cleanup.
8. **8 distinct `border-radius` values** (4 / 6 / 7 / 8 / 10 / 14 / 50% / 999px). Buttons are 7px, cards 10px, inputs 6px, icon buttons 8px. Pick two radii plus pill/circle.
9. **No `@media (hover: hover)` / `(pointer: coarse)`.** Card hover-swap, `6px 6px 0` hover shadow, and `filter: brightness` all fire on tap-and-hold on coarse pointers. Coarse should skip hover chrome and keep the selected/focus styles.
10. **No `accent-color`, scrollbar, or `text-wrap: balance` on headings.** Low priority; listed so a modernization pass does not rediscover them.
11. **`.modal-backdrop` and `.mobile-drawer-backdrop` share the same visual recipe** (fixed inset, 20, `rgba(0,0,0,0.55)`) and are copy-pasted three times. One `.backdrop` class, two roles.

---

## 13. Second-Pass Checklist Additions

Append to §7; do not replace it.

- [ ] **Step 7: Delete unused tokens and no-ops** — `--shell-gap`, `--choice-hover` (or wire it to `.choice-card:hover`), empty `strong::after`, redundant `.choice-card.auto` / hover / `.summary-card:hover` restates.
- [ ] **Step 8: Decide orphan emitters** — drop or style `.has-media`, `.positive`, `.dealer-turnstile`, `.summary-action-button`, `.structured`, `.body-setup-group`. This is the only step that may touch `app.js` / `index.html`; keep it in its own PR if it does.
- [ ] **Step 9: Scope the `button` element rule** — introduce an explicit primary class and stop paying the 11× `filter: none` tax. Must preserve the CSS-text assertions on `.choice-card` / `.vehicle-setup-chip`.
- [ ] **Step 10: Finish reduced-motion and focus rings** — extend the reduce block to drawers, interior groups, and hover-swap images; add `:focus-visible` on primary, ghost, icon, step-link, and toast-dismiss.
- [ ] **Step 11: Tokenize stacking, type, radius, and the carbon fill** — named `--z-*`, a 4-step type scale, 2 radii, one carbon utility used by `body` and the paint stage.
- [ ] **Step 12: Prefix companions** — per-selector `::marker` companions, unprefixed `line-clamp`, `*::before, *::after` box-sizing.

**Still out of scope until explicitly approved:** changing dealer-submission markup or Turnstile behavior (styling the mount is fine; changing the widget is not), any visual redesign, workbook/generator/registry edits.

**Validation for a later implementation pass (not run here):** `node --test tests/stingray-form-regression.test.mjs tests/multi-model-runtime-switching.test.mjs`, visual check at 375 / 760 / 887 / 1120 / 1400, `git diff --check`. This addendum is diagnosis only.
