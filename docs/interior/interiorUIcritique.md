# Interior UI critique

Strongest parts:

- The left step rail is clear and makes the interior sequence obvious: Seats → Interior Color → Seat Belt → Interior Trim.
- The Seat Belt step is the strongest interior screen because it uses actual visual assets. Users can immediately compare black, natural, orange, blue, red, and yellow.
- The active step styling is readable, and the red brand color gives the flow a consistent visual language.
- Compatibility messaging exists on Interior Color: “Showing colors compatible with AQ9 GT1 Bucket Seats.” That is the right kind of dependency cue.

Main issues:

1. Interior is fragmented across too many equal-weight steps
   Seats, Interior Color, Seat Belt, and Interior Trim are separate top-level steps, but customers think of these as one composed interior. The UI never gives a clear “your interior so far” view while making those choices.

Recommendation:
Add an Interior composition/review panel across steps 7–10:

- Seat
- Interior color
- Seat belt
- Interior trim
- Total interior delta
- Any compatibility locks

This could be a small sticky panel or summary strip inside the interior steps.

2. Interior Color lacks visual confirmation
   The Interior Color step is mostly text cards. For a color decision, the UI should show at least a swatch or interior thumbnail. Currently:

- HTA Jet Black, HUP Sky Cool Gray, HUQ Adrenaline Red all look structurally identical.
- The descriptions repeat “Mulan leather seating surfaces with perforated inserts.”
- The selected state is only a thin red outline around the inner card/card group.

Recommendation:
Use swatches or interior thumbnails for each color. Add an explicit “Selected” badge or checkmark. The red border alone is too subtle for a major visual choice.

3. The card-within-card pattern adds noise
   Interior Color cards have an outer section card and an inner selectable card. This creates duplicated labels:

- HTA Jet Black
- HTA
- HTA Jet Black
- $0

The hierarchy feels heavier than the actual choice requires.

Recommendation:
For one-choice interior color groups, collapse the nested card structure into one selectable card:
RPO + name + price + description + image/swatch + selected state.

4. “1 choice” is technically accurate but customer-hostile
   The small “1 choice” label reads like internal grouping metadata. It does not help the buyer understand why the card is presented that way.

Recommendation:
Either remove it or replace it with something customer-facing:

- “Available”
- “Compatible”
- “Included with selected seats”
- Or omit entirely when there is only one actual selectable row.

5. Compatibility copy needs a next action
   “Showing colors compatible with AQ9 GT1 Bucket Seats” is helpful, but it does not tell users what to do if they want more interior colors.

Recommendation:
Add action-oriented copy:
“Showing colors compatible with GT1 Bucket Seats. Change seats to see additional interior colors.”

If technically possible, link “Change seats” back to the Seats step.

6. Seats step is too sparse for a major choice
   The Seats step has two cards:

- AQ9 GT1 Bucket Seats, $0
- AE4 Competition Sport Bucket Seats, $1,095

But there is no image, no feature difference, no comfort/performance cue, and no explanation of downstream color compatibility.

Recommendation:
Add short comparison cues:

- GT1: standard touring bucket seats
- AE4: competition-style sport bucket seats
- “Changing seats may affect available interior colors”

Even one thumbnail per seat type would improve confidence.

7. Seat Belt step is visually better, but copy still feels internal
   The belt images are useful. However, the group header says:
   “RELATED OPTIONS”
   “Stingray seatbelt colors are mutually exclusive; included 3LT interior seatbelts lock peers.”

That reads like workbook/rule language, not customer language.

Recommendation:
Rewrite as:
“Choose one seat belt color. Some premium interiors include matching seat belts automatically.”

Keep internal rule phrasing out of the customer UI.

8. Interior Trim mixes true trim with functional tech
   Interior Trim shows:

- UQT Performance Data and Video Recorder, $1,495
- D30 Color Combination Override, unavailable, $1,495

UQT does not feel like “interior trim” to a buyer; it sounds like performance/technology. D30 sounds like a configurator rule artifact rather than a purchasable feature.

Recommendation:
Review section ownership:

- UQT may belong better in Performance/Technology or Accessories depending on workbook intent.
- D30 should probably be hidden, renamed, or moved into a clearly explained “Unavailable with current selections” area.

9. Disabled unavailable card is confusing
   D30 appears greyed out but still shows $1,495 and an info icon. It is not clear whether:

- It was selected and became unavailable
- It could become available later
- It is a rule-only placeholder
- It affects pricing

Recommendation:
For unavailable options:

- Show a reason directly on the card.
- Consider suppressing price unless it is actionable.
- Use copy like “Not available with current interior color” instead of only “Unavailable.”

10. Summary overlay does not help interior decisions enough
    The Build Summary drawer shows total build cost and selected RPOs, but while on Interior Trim it does not immediately show an Interior grouping in the visible area. It also dims and competes with the main selection area.

Recommendation:
Add grouped summary sections by customer category, including Interior:

- Seats
- Interior Color
- Seat Belt
- Interior Trim

Also consider a compact inline interior summary instead of requiring the full drawer.

Priority fixes I would recommend first:

A. Add selected checkmark/badge and visual swatches/images to Interior Color.
B. Replace “1 choice” and internal rule copy with customer-facing compatibility language.
C. Add an Interior composition summary across steps 7–10.
D. Move or reframe confusing Interior Trim items, especially D30.
E. Add completion/selected indicators to the left step rail so users know which interior choices are done.

Validation run:

- Browser inspection of localhost:8000.
- Checked Seats, Interior Color, Seat Belt, Interior Trim.
- Browser console reported no JS errors.

No repo files, workbook sheets, generated artifacts, or runtime behavior were changed.
