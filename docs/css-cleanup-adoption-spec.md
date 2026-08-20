# CSS Cleanup Adoption Spec (`form-app/styles.css`)

Date: 2026-08-19
Status: Proposed — not implemented
Change class: styling-first (Steps 1–5, 7, 9–12 are CSS-only; Step 8 is the only HTML/JS step; Step 6 is deferred)
Owning audit: `docs/css_coverage_audit.md` §7 and §13

## Purpose

Adopt the audit's twelve-step checklist against `form-app/styles.css` (2,891 lines,
411 rule blocks) without breaking the CSS-text assertions that two runtime test suites
make directly against this file.

The audit is the diagnosis. This spec is the adoption contract. Where verification
disagreed with the audit, or where a later audit section constrained an earlier
checklist item, this file wins.

## Constraint that drives the whole plan: the stylesheet is test-asserted source text

`form-app/styles.css` is hand-authored (no generator writes it — `generate_form.py` /
`generate_registry.py` only produce `form-output/*` and `form-app/data.js`), but it is
**read as raw text and regex-asserted** by:

- `tests/stingray-form-regression.test.mjs` — reads it into `stylesSource` at line 19;
  ~53 assertions, plus helpers `cssOrderFor()` (line 55) and `cssBlock()` (line 61).
- `tests/multi-model-runtime-switching.test.mjs` — line 855, two `.choice-relationship-badge`
  assertions.
- `tests/validation_catalog.json` line 585 lists it as a read input of the styling lane.

Three properties of those assertions constrain every step:

1. **Flat-block regexes.** `cssBlock()` matches `(?:^|\n)<selector>\s*\{[\s\S]*?\}` — a
   non-greedy match to the *first* `}`. Any nested block inside a component (audit Step 6)
   makes the match stop early and silently truncate. Native CSS nesting is therefore
   **not safe** for any selector these tests touch.
2. **Property-order-sensitive regexes.** e.g. `.vehicle-setup-chip` at stingray line 1057
   asserts `justify-self` → `width` → `max-width` → `min-width` in that written order.
   Reordering declarations during dedupe breaks it.
3. **Media-block slicing by source position.** Stingray lines 812–821 slice the file by
   `indexOf("@media (max-width: 1120px)")`, `indexOf("@media (min-width: 761px) and (max-width: 887px)")`,
   `indexOf("@media (max-width: 760px)", narrowDesktopStart)`, and
   `indexOf("@media (prefers-reduced-motion: reduce)")`, and assumes breakpoints appear in
   that source order. The test documents the split 760px blocks in a comment
   ("the paint step adds an earlier scoped 760px block").

Current `@media` source order (verified): 1400 (701), 760 (711), 1121 (2198), 1120 (2227),
761–887 (2316), 760 (2378), reduced-motion (2882).

## Source-of-truth decision

- `form-app/styles.css` owns presentation. It is source, not a generated artifact.
- `form-app/index.html` + `form-app/app.js` own which class names exist. A CSS selector is
  dead only when neither emits it. A class name is an orphan emitter when HTML/JS emit it
  and CSS has no rule.
- The two `.test.mjs` files above own the CSS contract. Where cleanup and an assertion
  conflict, the assertion is updated **in the same commit, with the intent preserved** —
  never deleted to make a refactor pass.
- `docs/css_coverage_audit.md` is the diagnosis, not the contract. This checklist
  supersedes it where verification disagreed (most importantly: Step 6 is deferred, and
  Step 8 is the only authorized HTML/JS step).

## Verified state of the audit's claims

Re-checked against the live files:

| Audit claim | Verified |
| --- | --- |
| `.auto-reason` color set at 1446–1447 (`--warn`), overridden at 1557 (`--ok`) | Yes |
| 7 `@media` blocks, two at `max-width: 760px` (711, 2378) | Yes |
| 8 dead selector families | Present in CSS; all 8 have zero emitters in `app.js`/`index.html` |
| `.summary-drawer-icon`, `.vehicle-setup-intro`, `.choice-relation-count` | Dead in CSS, but each has a `doesNotMatch` **negative** assertion (stingray 770 / 1027; multi-model 883) proving the DOM must never re-emit them. Those assertions stay. |
| `.auto-reason` is live | Yes — `app.js:2009` emits it; `stingray:1239` asserts it |
| `--shell-gap` defined, never consumed as `var(--shell-gap)` | Yes. Stingray 804 already forbids `gap: var(--shell-gap)`. |
| `--choice-hover` defined, never consumed as `var(--choice-hover)` | Yes. `--choice-hover-border` / `--choice-hover-shadow` are live. |
| Empty `strong::after` at 850–852 | Yes — `content: ""` only. |
| Orphan emitters `.has-media`, `.positive`, `.dealer-turnstile`, `.summary-action-button`, `.structured`, `.body-setup-group` | Yes — present in HTML/JS, absent from CSS. |
| Unscoped `button` (203–217) plus 11 `filter: none` resets | Yes. |
| `prefers-reduced-motion` misses `.interior-group`, hover-swap images, both drawers | Yes. |
| Inter named at `styles.css:56`, never loaded | Yes — no `@font-face`, no Google Fonts link, no local files. |
| CSS-text helpers make nesting unsafe | Yes — `cssBlock()` stops at the first `}`. |

## Scope

Step numbers match the audit. They are not renumbered when a step is deferred.

| Steps | Surface | Appearance rule |
| --- | --- | --- |
| 1, 2, 4, 7, 12 | CSS only | Zero rendered-appearance change |
| 3 | CSS only | Cascade-sensitive; ships only with equivalence evidence |
| 5 | CSS only | Token introduction is zero-change; weight/palette collapse is visible and optional |
| 6 | none | Deferred. Not a shipping PR under this spec. |
| 8 | HTML/JS, and CSS only if an orphan is given a rule | Default is delete unused hooks, not invent new looks |
| 9, 10, 11 | CSS only | Visible or interaction-visible; each ships alone |

Out of scope unless a later, separately approved revision of this spec pulls them in:

- Audit §6 items 2–5: `color-mix`, container queries, logical properties, subgrid.
- Audit §12 items 9–10: `@media (hover: hover)` / `(pointer: coarse)`, `accent-color`,
  scrollbar styling, `text-wrap: balance`.
- Loading Inter (or any new font file / network stylesheet). The live face is the system
  stack; this spec only authorizes dropping the unused family name.
- Inventing success styling for `.positive`, trim-like styling for `.body-setup-group`,
  or any dealer-submission / Turnstile behavior, payload, or widget change.
- Workbook, generator, registry, or deployment edits.

Audit §12 item 11 (shared backdrop recipe) is **not** a new class. Step 4 already deletes
the duplicate media copies of `.mobile-drawer-backdrop:not([hidden])`. Do not introduce
`.backdrop` here — that would be an HTML change and belongs only if Step 8 is later
expanded.

## Plan — one PR per shipping step, in this order

Each shipping step is independently revertable and ends green. Ordering matters: dead CSS
first, then unused tokens/no-ops, then collision fixes, then cascade work, then tokens,
then the one HTML/JS pass, then the visible control/a11y/token-scale work.

Step 6 is listed so the numbers stay aligned with the audit. It does not ship.

### Step 1 — Remove dead selectors (~80 lines)

Remove rules for: `.model-picker` / `.model-picker select` (189, 199), `.summary-drawer-icon`
(441), `.vehicle-setup-intro` and descendants (736–751, 2687), `.choice-relation-eyebrow`
(1103, 1109), `.choice-relation-count` (1133), `.choice-note` (1433, 2818, 2828),
`.customer-card` (1653), `.tooltip-tail` (2060).

Before each removal, re-grep `form-app/app.js` and `form-app/index.html` for the bare class
string (template literals included) — the audit's emitter analysis is re-proven at edit time,
not trusted.

Test impact: none expected. The three negative assertions target HTML/JS sources, not CSS.
Add one new assertion to `tests/stingray-form-regression.test.mjs`:
`assert.doesNotMatch(stylesSource, /\.model-picker|\.tooltip-tail|\.customer-card|\.choice-relation-eyebrow/)`
so the dead selectors cannot silently return — same pattern as the existing
`.nested-standard-equipment` guard at line 891.

Risk: low.

### Step 2 — Fix priority and collision bugs

- `.auto-reason`: drop it from the 1446 `.disabled-reason, .auto-reason` group's `color`
  declaration by splitting the shared block into (a) shared `font-size`/`font-weight` for both
  and (b) `color: var(--warn)` on `.disabled-reason` alone; delete the 1557 override and set
  `color: var(--ok)` at the single definition point. Rendered color must remain `--ok`.
- Merge the three duplicate selector pairs inside `@media (max-width: 760px)` into one block
  each, keeping the later (winning) values: `.choice-panel` (2626 + 2779),
  `.vehicle-setup-next-action` (2682 + 2860 → `display: none` wins, so the flex properties
  become dead and are dropped), `.setup-choice-grid` (2630 + 2691).

Test impact: check `stingray:1239` still matches (it asserts the emitted class list, not the
rule) and that no `cssBlock(".choice-panel")`-style assertion depends on the earlier block.

Risk: medium — merging duplicates changes which declarations survive. Diff the computed style
of each merged selector at 375px and 760px before/after.

### Step 3 — Consolidate the two `max-width: 760px` blocks

Merge the paint/vehicle-stage rules at 711–729 **forward into the block at 2378**, at the top
of that block. Direction is not optional: merging backward (into position 711) would move the
mobile block before `@media (max-width: 1120px)`, breaking the position-based slicing at
stingray 812–821 and inverting cascade order against the 1120px and 761–887px blocks.

Update the now-stale comment at stingray 815–817 ("the paint step adds an earlier scoped 760px
block") and simplify `mobileStart` to a plain `indexOf` once the earlier block is gone.

Verify cascade equivalence: the moved rules currently apply *before* the 1120px and 887px
blocks; after the move they apply after. Confirm no selector in those two blocks also matches
the moved paint/swatch selectors (`.vehicle-stage`, swatch grid). If any does, the moved rules
must keep their original relative position instead and Step 3 is dropped with a note here.

Risk: medium-high — this is the only step that changes cascade order. It ships alone.

### Step 4 — Deduplicate re-declared properties

Remove the identical re-declarations the audit names: `.summary-panel` 9 properties at 2253,
`.mobile-drawer-backdrop:not([hidden])` at 2277 and 2748 (keep 1605),
`#requirementsCard`/`#selectedRposCard`/`#autoAddedCard`/`#summaryOverviewCard` order values at
2758–2771 (keep base 1941–1954), `.topbar { align-items: center }` in the two redundant media
blocks, `.step-link` at 2715.

Guard rails:
- `cssOrderFor()` (stingray 55) finds the **first** `order:` after a selector — keeping the base
  declarations means order assertions still resolve. Confirm each affected assertion after edit.
- Line 833 asserts `.mobile-drawer-backdrop:not([hidden])` against `baseStyles` only (the slice
  before the 1120px block) — keeping 1605 satisfies it.
- Line 829 asserts `.summary-panel` fixed/translateX against `baseStyles` — keeping base 1568–1581
  satisfies it; only the 2253 copy goes.
- Do **not** reorder surviving declarations (constraint 2 above).
- Do **not** invent a shared `.backdrop` class. Deleting the duplicate media copies is enough.

Risk: low-medium. A "redundant" declaration is only redundant if no intervening rule overrides
it; verify each by computed style at the breakpoint, not by textual equality alone.

### Step 5 — Normalize font weights and palette tokens

Add `:root` tokens and map live values. This step does **not** absorb Step 7 (dead tokens /
no-ops) or Step 11 (type scale, radius, stacking, carbon utility). Those stay separate so a
rejected collapse does not block mechanical cleanup.

- Weights: 400 → `--fw-regular`, 600/650 → `--fw-medium` (600), 700/750 → `--fw-bold` (700),
  800/850/900 → `--fw-heavy` (800). Collapsing 650/750/850 is a **visible** change on a variable
  font. Do it as two commits: first introduce tokens at the existing 9 values, then collapse to 4
  with before/after screenshots of the step rail, choice cards, summary rows, and stage pills.
- Palette: `#cfd3d6` (6 uses), `#1a1d1f`, `#101214`, `#0f1112`, `#172026`, `#f0c07a`,
  `rgba(232,161,60,0.4)`, `rgba(53,184,93,0.4)` → named `:root` variables.

Test impact: any assertion matching a literal weight or hex must be updated to the token name.
Grep the two test files for `font-weight` and `#` literals before editing.

Risk: medium (weight collapse is user-visible by design). If the collapse is rejected on review,
ship the token-introduction commit and stop. Do not start Step 11 until the introduction half
of Step 5 has landed.

### Step 6 — CSS nesting: deferred

Full nesting conflicts head-on with `cssBlock()`'s first-`}` match and with every
`/<selector>\s*\{[\s\S]*?<property>/` assertion.

**This spec defers nesting.** The CSS-text test contract is the current safety net for a
stylesheet with no visual regression harness. Step 6 is not a shipping PR.

If a later revision adopts it anyway: first replace text-regex CSS assertions with a parsed-CSS
helper (e.g. a small `tests/lib/css.mjs` that walks rules and resolves nesting), migrate all
~55 assertions to it, prove the suite still fails on a deliberately broken rule, and only then
nest — starting with one component (`.info-tooltip`) as a pilot. That helper is a prerequisite
PR, not part of a nesting PR, and is outside this spec's current approval.

### Step 7 — Delete unused tokens and no-ops

CSS-only. Zero rendered-appearance change. Ships after Step 4 so the file is already smaller,
and before Step 8 so orphan-emitter work does not restyle dead tokens.

Delete or collapse, after a fresh grep proves no `var()` consumer:

- `--shell-gap` (line 38). Keep the stingray 804 negative assertion.
- `--choice-hover` (line 29), unless a computed-style check shows a card that should have been
  using it. Default is delete, not wire: wiring `#181d20` onto `.choice-card:hover` would
  **change** the current hover (which restates `var(--choice-bg)`). Wiring is a Step 11 decision.
- Empty `.vehicle-setup-chip[data-setup-chip-state="complete"] strong::after` (850–852).
- Redundant restates that do not change computed style: `.choice-card.auto` `border-color` /
  `background` (keep `outline-color: var(--ok)`), `.choice-card:hover` `background` (keep
  border + shadow), `.summary-card:hover` `background` (keep `border-color`). If removing a
  restate would drop a property the transition list implies, drop the unused `box-shadow`
  transition on `.summary-card` in the same commit — it never fires.
- Unused `Inter` family name on `body` (line 56). Do not add `@font-face` or a font CDN.
  After the edit, `font-family` should start at `ui-sans-serif`. Confirm no test asserts `Inter`.
- Duplicate visually-hidden recipes: keep `.sr-only` as the single utility; point
  `.reset-label, .download-label` at the same declarations (or replace those classes with
  `sr-only` in a later Step 8 if HTML is opened). Do not change clipping behavior.

`--choice-bg` being byte-identical to `--panel-strong` is recorded, not merged here. Merging
those two tokens is a Step 11 call because it changes the token vocabulary tests may grow to
assert.

Add a stingray `doesNotMatch` for `--shell-gap:` and `--choice-hover:` if those tokens are
deleted, so they cannot return.

Risk: low. Computed-style check on a complete setup chip, a selected auto card, a hovered
summary card, and the body font stack.

### Step 8 — Decide orphan emitters

This is the only step that may edit `form-app/app.js` or `form-app/index.html`. It ships
alone. Default for each orphan is **delete the unused hook**, not invent a look. Re-grep
immediately before editing.

| Class | Default under this spec | Not authorized here |
| --- | --- | --- |
| `.has-media` | Remove the four `classes.push("has-media")` calls. Hover-swap already keys off `.has-hover-media`. | A new media-card layout. |
| `.positive` | Remove the unused class from the complete-requirements `<li>`. Keep `.empty`. | A new success color or checkmark. |
| `.structured` | Remove it from the tooltip-content class list. Layout already comes from `.tooltip-content` / `.tooltip-list`. | A new tooltip template. |
| `.summary-action-button` | Remove the extra class from the mid-width Build Summary control. | A new toolbar variant. |
| `.body-setup-group` | Remove the unused class from `renderVehicleSetupPanel(...)`. Panel defaults already apply. | Copying `.trim-setup-group` styling onto body setup. |
| `.dealer-turnstile` | Leave the HTML class and add no CSS. The mount is a dealer-boundary hook; unstyled is the current live look. | Changing Turnstile widget, size, sitekey, or submit UX. |
| `data-has-next` | Inspect only. Do not add CSS. `#mobileNextStep` is `display: none` at 760px. | Re-enabling a mobile Next control. |

If a default delete is later rejected, record the new decision in this table and stop. Do
not substitute a visual invention to "use" the class.

Test impact: any HTML/JS negative assertion that already forbids a deleted string stays.
Add focused `doesNotMatch` guards for `has-media`, `class="empty positive"`, and
`summary-action-button` if those strings disappear.

Risk: medium — this is the only runtime-source edit. No dealer payload, modal, or Turnstile
script change.

### Step 9 — Scope the `button` element rule

CSS-only, after Steps 1–5 and 7 so most dead overrides are already gone. Visible if any
control was depending on the unscoped accent fill.

Replace the unscoped `button` chrome (203–217) with:

1. A true reset on `button` (`font: inherit`, `cursor: pointer`, min-height 44px, no accent
   fill / uppercase / glow).
2. An explicit primary class (name it `.primary-button` unless a live class already means
   that — do not invent a second primary). Apply that class in Step 8 if the HTML/JS pass
   has not yet landed; if Step 8 already closed, this step may add the class to existing
   primary actions only: `#submitDealerButton`, `#summarySubmitButton`,
   `#dealerSubmitConfirmButton`, `#confirmActionConfirmButton`, and the in-panel Continue /
   Next actions app.js already renders as bare `<button>`.

That HTML touch is allowed only for adding the primary class. It does not reopen Step 8's
orphan table.

Delete the 11 `filter: none` resets that exist only to undo `button:hover { filter:
brightness(1.08) }` once the hover filter lives on the primary class.

Preserve CSS-text assertions on `.choice-card` and `.vehicle-setup-chip` (they must keep
`text-transform: none`, `letter-spacing: 0`, `box-shadow: none` unless those are now
inherited from the reset and the tests are updated with the same intent).

Risk: high. Ships alone. Computed-style matrix before/after at 375 / 760 / 1120 for primary,
ghost, icon, step-link, chip, choice-card, toast-dismiss, and modal-close.

### Step 10 — Finish reduced-motion and focus rings

CSS-only. Interaction-visible. Ships after Step 9 so new `:focus-visible` rules land on the
scoped control model, not the unscoped `button`.

- Extend `@media (prefers-reduced-motion: reduce)` to `.interior-group`,
  `.choice-media.has-hover-media img`, `.summary-panel`, and `.step-rail`. Keep the existing
  six selectors.
- Narrow or remove `will-change: opacity` on hover-swap images. Prefer no permanent
  `will-change`; if a hint stays, attach it only under `@media (prefers-reduced-motion: no-preference)`
  plus `:hover` / `:focus-visible`.
- Add designed `:focus-visible` on primary, `.ghost-button`, `.reset-icon-button`,
  `.download-icon-button`, `.step-link`, and `.toast-dismiss`. Reuse the existing 3px
  `var(--accent-glow)` ring already used by fields and choice cards. Do not remove
  `outline: none` from field `:focus-visible` without keeping that ring.

Do not add `@media (hover: hover)` in this step.

Risk: medium. Keyboard-focus and reduced-motion checks are required in addition to the
six-viewport visual pass.

### Step 11 — Tokenize stacking, type, radius, and the carbon fill

CSS-only. Visible if type or radius collapse lands. Ships after the introduction half of
Step 5. Same two-commit pattern: introduce tokens at current values, then collapse only
with approved screenshots.

- `--z-stage`, `--z-footer`, `--z-docked`, `--z-backdrop`, `--z-drawer`, `--z-toast`,
  `--z-tooltip`, `--z-tooltip-floating` mapped to the live 6 / 5 / 1 / 20 / 30 / 60 /
  80–90 / 120 scale. Do **not** restack the modal under toasts or tooltips in this step;
  retuning those layers is a separate product decision.
- Type scale tokens for the live sizes (`--fs-2xs` … `--fs-xl`) at current px values first.
  Collapse 9 / 10 / 11.5 / 12.5 only in the second commit.
- Radius tokens for the live 4 / 6 / 7 / 8 / 10 / 14 / 50% / 999px set. Collapse toward
  two radii plus pill/circle only in the second commit.
- One carbon-fill utility (or `:root` background-image tokens) shared by `body` and the
  sticky paint stage, so the 6×6 checker cannot drift.
- Optional: collapse the 15 `rgba(255,255,255,α)` stops onto 4–5 surface tokens. Second
  commit only.
- Optional: merge `--choice-bg` into `--panel-strong` if both still match after Step 5.

Risk: medium. The introduction commit must be visually identical. Collapse commits are
rejected without before/after shots of the paint stage, a choice grid, the summary drawer,
and the topbar.

### Step 12 — Prefix companions

CSS-only. Zero rendered-appearance change on current WebKit/Blink. Ships last so it does
not collide with Step 3's 760px merge or Step 10's motion block.

- Add `summary::marker { display: none }` beside each of the three
  `summary::-webkit-details-marker` rules (988, 1189, 2165).
- Add unprefixed `line-clamp: 3` / `line-clamp: unset` beside the two `-webkit-line-clamp`
  declarations (2825, 2831). Keep the `-webkit-box` recipe.
- Expand `* { box-sizing: border-box }` to `*, *::before, *::after`.

Risk: low. Spot-check a disclosure caret in Safari and Firefox and a clamped note at 375px.

## Companion surfaces

| Surface | Action |
| --- | --- |
| `tests/stingray-form-regression.test.mjs` | Updated in Steps 1, 3, 4, 5, 7, 9, 10 (assertions + stale comment) |
| `tests/multi-model-runtime-switching.test.mjs` | Inspect at each step; `.choice-relationship-badge` rules (line 855–857) are not touched by Steps 1–7 or 12. Re-check in 8–11. |
| `tests/validation_catalog.json` | Inspected — styling lane already lists `form-app/styles.css` as a read; no change unless Step 8 adds a new HTML/JS assertion file (it should not) |
| `form-app/styles.css` | Edited in every shipping step except that Step 8 may be HTML/JS-only |
| `form-app/index.html`, `form-app/app.js` | Read-only except Step 8 (orphan table) and the primary-class additions allowed in Step 9 |
| `form-app/index.html` `?v=2` cache-bust (line 8) | Bump on every step that edits `styles.css` |
| `README.md` line 44 | Inspected — describes the file, no change |
| `docs/css_coverage_audit.md` | Diagnosis record; leave findings intact. It already points at this twelve-step checklist. |
| `docs/route-map.md` | Inspected — covers generated-data flow only, no CSS ownership claim; no change |
| `fable5loop/STATE.md` | `Current handoff` block updated after each landed step, per AGENTS.md §9 |
| Dealer submission surface | Payload, endpoint, Turnstile script, and submit UX untouched. Step 8 leaves `.dealer-turnstile` as an unstyled mount. |

## Validation per step

1. `node --test tests/stingray-form-regression.test.mjs tests/multi-model-runtime-switching.test.mjs`
   (full suite for Steps 3, 4, 8, 9, and 10).
2. Visual check of `form-app/index.html` at 375px, 760px, 887px, 1120px, 1400px, covering: model
   setup, paint step, an option step with relational groups, customer form, summary drawer open
   and closed, a disabled option, an auto-added option. Steps 9 and 10 also require keyboard
   focus on primary / ghost / icon / step-link / toast-dismiss and a reduced-motion pass.
3. `git diff --check`.
4. Line-count delta reported per step against the 2,891-line baseline.

A step that cannot show a clean visual diff at all six viewports does not ship; it is reduced or
dropped, and this file records which.

## Acceptance criteria

- Steps 1, 2, 4, 7, and 12 land with zero rendered-appearance change and a green suite.
- Step 3 lands only with cascade-equivalence evidence, or is dropped with the reason recorded here.
- Step 5 lands tokens; the weight collapse lands only with approved before/after screenshots.
- Step 6 stays deferred. No nesting PR ships under this spec.
- Step 8 lands only the orphan-table defaults (or a recorded deviation). No new product look.
- Step 9 lands with a computed-style matrix for the eight control types named in that step.
- Step 10 lands with keyboard-focus and reduced-motion evidence.
- Step 11's introduction commit is visually identical; collapse commits need approved shots.
- No dead selector removed in Step 1 is re-introduced (guard assertion in place).
- Unused tokens removed in Step 7 stay gone (guard assertion in place).
- Every CSS-text assertion in both test files either still passes unchanged or was updated with
  its original intent visible in the diff.

## Delivery

Per AGENTS.md §12 pull-request-only delivery: each shipping step reaches `main` through its
own pull request; no direct commits. Analysis and this spec do not authorize implementation —
implementation begins on explicit approval, one listed step at a time, in the order above.
