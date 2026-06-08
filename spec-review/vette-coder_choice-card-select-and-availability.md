# Task: option-card selected state (offset ring) + stop unavailable-pill layout shift

You are `vette-coder`. Make two surgical changes to the Corvette configurator's option
cards. Work only in the files you need. Keep the diff minimal and do not refactor
surrounding code.

## Files
- `form-app/styles.css` — active stylesheet containing `.choice-card`, `.choice-card.selected`,
  `.choice-state`, `.disabled-reason`, `.choice-relationship-badge`, tooltip classes.
- `form-app/app.js` — active static runtime. The affected renderers are
  `renderChoiceCard`, `renderInteriorCard`, and `renderContextCard`; all already use
  `renderStatePill()` for tooltip-capable `.choice-state` pills.
- `tests/stingray-form-regression.test.mjs` — runtime/CSS regression coverage for the
  selected ring and option-card availability slot.
- `tests/multi-model-runtime-switching.test.mjs` — context-card disabled-pill coverage.

## Codebase-fit adjustment

The original spec assumed a separate `.disabled-reason` paragraph was appended. Current
`form-app/app.js` already renders disabled and auto-added messages through `renderStatePill()`,
which returns `.choice-state ... info-tooltip` when a reason is present. The implementation
therefore adds a small generic `renderChoiceAvailability()` wrapper and places the existing
pill inside it, instead of changing tooltip mechanics or introducing a new paragraph path.
The constant slot is applied to option, interior, and context choice cards because all three
share `.choice-card` styling and can render availability pills. Model cards are unchanged
because they do not have an unavailable state in the current renderer.

---

## Task 1 — Replace the selected state with a crisp offset ring

The current `.choice-card.selected` uses inset box-shadows + a gradient fill. Remove all of
that. The new selected indicator is a sharp accent **outline that sits just outside the card
with a gap** — no inner fill, no glow, no blur. The interior of the card must not change on
select.

### Edit the base `.choice-card` rule (around line 932)
Add a reserved transparent outline and include `outline-color` in the transition so it
animates. Do **not** change anything else in this rule.

```css
.choice-card {
  /* ...keep all existing properties... */
  outline: 2px solid transparent;   /* reserved so the ring can animate in, no layout impact */
  outline-offset: 3px;
  transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease, outline-color 140ms ease;
}
```

### Replace the selected rules (currently lines ~953–971)
```css
.choice-card.selected {
  outline-color: var(--accent);
}

.choice-card.selected:hover {
  border-color: #b8a995;
  outline-color: var(--accent-dark);
  box-shadow: var(--choice-hover-shadow);
}
```
Notes:
- Leave the card border at `var(--line)` when selected — the red comes only from the ring.
  The thin neutral border inside the red ring is intentional.
- Delete the `background-image` gradient and all `inset ...` box-shadows from the old
  selected / selected:hover rules.

### Mirror the ring for the auto-added (green) variant (currently lines ~979–992)
Auto-added options should read the same way in green, not with a fill or inset.
```css
.choice-card.auto {
  border-color: var(--line);
  background: var(--choice-bg);
  outline-color: var(--ok);
}

.choice-card.selected.auto {
  outline-color: var(--ok);
}
```
Remove the green gradient + inset box-shadows from the old `.selected.auto` rule.

### Keep keyboard focus distinct from selected
The solid outline now means "selected," so do not let `:focus-visible` reuse a plain solid
outline or it will be ambiguous. Add an explicit focus ring that reads differently (a soft
box-shadow ring works and won't shift layout):
```css
.choice-card:focus-visible {
  outline-color: transparent;            /* don't show the selected-style ring on focus */
  box-shadow: 0 0 0 3px rgba(178, 34, 52, 0.35);
}
.choice-card.selected:focus-visible {
  outline-color: var(--accent);          /* keep the selected ring */
  box-shadow: 0 0 0 3px rgba(178, 34, 52, 0.35);
}
```

### Tuning dials (leave at defaults unless asked)
- Gap width: `outline-offset` (3px default; 4–5px for more breathing room).
- Ring weight: `outline-width` (2px default).

---

## Task 2 — Stop the layout shift when the "unavailable" pill populates

### The problem
When an option becomes unavailable, the render code appends a `.choice-state` pill and a
`.disabled-reason` paragraph into the card's grid. These are new rows, so the card grows
taller. Because `.choice-grid` rows size to their tallest card, the whole row — and
everything below it — jumps. A single selection can flip many options at once, so the jump
is large.

### The fix: reserve a constant, single-line availability slot in every card
Give every card a persistent availability row that is always present (even when the option
is available), sized to one pill. The pill populates into the reserved space instead of
adding height, so card height is constant across availability toggles. The reason text moves
into the pill's tooltip so the slot never needs more than one line.

This keeps cards **flexible** (they still grow with longer names/notes) — only the
availability area is height-stable. Do **not** give the card a fixed height.

```
BEFORE (toggling availability changes height -> row jumps)
  available                unavailable
  +----------------+       +----------------+
  | SNG       $320 |       | SNG       $320 |
  | Name           |       | Name           |
  | note...        |       | note...        |
  +----------------+       | [Unavailable]  |  <- appended rows
                           | reason text... |  <- card grows, row jumps
                           +----------------+

AFTER (slot reserved in both -> height constant)
  available                unavailable
  +----------------+       +----------------+
  | SNG       $320 |       | SNG       $320 |
  | Name           |       | Name           |
  | note...        |       | note...        |
  | (reserved)     |       | [Unavailable]  |  <- reason now in the pill's tooltip
  +----------------+       +----------------+
```

### Markup change (in the card render code)
Always emit a single availability container as the last child of `.choice-card`, regardless
of availability:
```html
<div class="choice-availability"><!-- pill injected here when unavailable --></div>
```
- When the option is **available**: leave the container empty.
- When **unavailable**: inject the existing `.choice-state` pill, and make it an
  `info-tooltip` carrying the reason (reuse the existing `.choice-state.info-tooltip` +
  `.tooltip-panel` mechanism). Do **not** also append a separate `.disabled-reason`
  paragraph into the flow — the reason lives in the tooltip now.

### CSS
```css
.choice-availability {
  min-height: 24px;          /* one pill row; reserved even when empty */
  display: flex;
  align-items: center;
}
.choice-availability:empty {
  /* stays reserved; do NOT set display:none */
}
```
If 24px doesn't exactly match your pill height, set it to the rendered pill height so the
empty and filled states are identical.

---

## What NOT to do
- Do **not** add a fixed `height` or a new `min-height` to `.choice-card` itself — only the
  `.choice-availability` slot gets a reserved min-height.
- Do **not** reintroduce any inset box-shadow, gradient, or background fill on the selected
  state. The interior stays unchanged; the ring is the only selected signal.
- Do **not** color the card border red on select — the ring carries it.
- Do **not** use `display:none` on the empty availability slot (that brings the shift back).
- Do **not** touch the hover shadow (`--choice-hover-shadow`) or unrelated rules.
- Do **not** widen the diff with reformatting or renames.

## Validate
1. Open the configurator. Select/deselect options: the ring appears **around** the card with
   a gap, crisp, no fill, no blur; the card interior doesn't change.
2. Confirm the selected ring animates in and respects `prefers-reduced-motion` (the existing
   reduced-motion rule already zeroes `.choice-card` transitions — verify it still applies).
3. Trigger an availability change that flips several options to unavailable (e.g., make a
   selection that disables others). Confirm cards do **not** change height and the grid does
   **not** jump. The "Unavailable" pill appears in the reserved slot; its reason shows on
   hover/focus via the tooltip.
4. Tab through cards: keyboard focus is clearly visible and distinct from the selected ring.
5. Check a card near the panel edge: the ring isn't clipped (the choice-panel padding should
   cover the 5px the ring extends; if it clips anywhere, reduce `outline-offset` or confirm
   `.choice-panel` padding ≥ outline-offset + outline-width).
6. Check mobile (`.choice-grid` becomes 1 column): ring, slot, and tooltip all behave.
7. Run the project's usual build/lint checks if it has them.
