# QA-4 Remaining Issues

These are the issues still requiring follow-up after the QA-3 new-issues implementation pass.

The QA-3 new issues for BC7 default selection, 5V7/5ZU availability, Section 8 ordering, section scroll reset, seat-price subtraction, and D30 user selectability were covered in the last pass and are not carried forward here.

## Still Existing

### **Issue 1**: Option names/descriptions still need a copy and display-field cleanup.

Original reference: `debug/qa-3.md` Issue 1

Current evidence:

- `opt_ahe_001`
  - Label: `Seat adjuster, driver power bolster`
  - Description: `driver power bolster`
  - Issue: repeated text.
- `opt_uqs_001`
  - Label: `Audio system feature`
  - Description: `Bose Premium 10-speaker system`
  - Issue: generic label requires the description to identify the option.
- `opt_uqh_001`
  - Label: `Audio system feature`
  - Description: `Bose Performance Series Sound System with 14 speakers`
  - Issue: generic duplicate label makes the two audio choices hard to scan.
- `opt_aq9_001`
  - Label: `GT1 Bucket Seats`
  - Description: `GT1 bucket`
  - Issue: label and description are repetitive.

Needed fix:

- Decide which fields should display in option cards and summary/export rows.
- Normalize duplicate/generic option copy across the generated data so cards do not rely on repeated or low-value descriptions.

### **Issue 3**: Summary/export still lacks a workbook-driven inclusion flag.

Original reference: `debug/qa-3.md` Issue 3

Current state:

- The full standard/included equipment dump is no longer exported.
- Selected options, selected interior, auto-added options, and price adjustments are exported.

Remaining gap:

- There is still no explicit workbook contract field that says which selected, included, or auto-added options should appear in the customer summary/export.

Needed fix:

- Wait for the workbook to add the inclusion flag.
- Once the contract exists, thread that field through the generator, JSON output, summary UI, JSON export, and CSV export.

### **Issue 4**: Display-only inactive labels still need a complete audit.

Original reference: `debug/qa-3.md` Issue 5

Current state:

- Rule-backed disabled rows can show more helpful `Requires...` or `Blocked by...` messages.
- `form-app/app.js` still has the generic fallback text `Display-only source row.` for inactive non-selectable choices when no rule-specific reason is found.

Remaining gap:

- Any customer-visible inactive/display-only row should explain the actual requirement or reason whenever possible.

Needed fix:

- Audit visible inactive rows across all steps.
- Replace generic fallback cases with workbook-backed or rule-derived reasons where the data supports it.
- Decide whether rows with no meaningful customer-facing reason should be hidden instead of shown with a generic disabled label.

## Not Carried Forward

### Color Override inactive-state issue

Original reference: `debug/qa-3.md` Issue 4

Reason:

- The current generated runtime does not expose Color Override as a selectable customer step.
- D30 remains available for color-override auto-add logic but is no longer directly selectable by the user.

Follow-up only needed if Color Override returns as a selectable customer-facing section.

## New Issues

- ### Issue 1: FE3 needs to have a front end option tile. It makes the suspension options look weird without it, and it is a valid option that can be selected and exported.
  - FE3 - Auto added when Z51 is selected, but can be overridden by FE4. Z51 rules that make FE1 and FE2 unavailable on selection should persist.
  - FE3 should be unselected when FE4 is selected and vice versa.

- ### Issue 2: Step 4 Exterior appearance- display_order change
  - Correct order:
    1. Roof
    2. Exterior Accents
    3. Badges
    4. Engine Appearance

- ### Issue 3: FE1 needs to be a default selected option. FE2 can be selected to override FE1, and Z51 can be selected to override both FE1 and FE2, making FE3 the default suspension selection when Z51 is selected.

- ### Issue 4: Spoiler section rules are not correct.
  - ZYC should not be unselected when another spoiler is selected, ie TVS. The only reason ZYC would become unselected is if GBA is selected as the exterior color since that is the only conflict for ZYC.
  - T0A should not make TVS or 5ZZ or 5ZU unavailable. These options are still available when T0A is selected, they just remove T0A if selected, but they should not be blocked by T0A. Need to update the rules and change the option labels that currently say "Conflicts with T0A" to "Removes T0A when Z51 is selected" and not be deactivated if one of the other spoilers is selected.

- ### Issue 5: If NWI is selected, it correctly unselects NGA, but if it is unselected, NGA should be selected automatically again since it is the default and there needs to be an exhaust color selected.

- ### Issue 6: Scroll reset to top is not working on 'next step' button click. Example: Just went from section 8 which is very long to section 9 which is very short, but the scroll position is still at the bottom of the page and you can't see the top of section 9 without manually scrolling up.

- ### Issue 7: 1LT AE4 interior color option HTJ should be set to automatic selection since there is only one interior color option available.

- ### Issue 8: Redundant Standard/Included equipment sections in the right sidebar. Keep the one that is currently in the "Selected Options" container and remove the free standing one that is at the bottom of the sidebar.

- ### Issue 9: Engine Appearance display_order change:
  - Correct order:
    1. BC7 - Add a "Requires ZZ3 Convertible Engine Appearance Package" label and a conditional availability rule like the other engine cover options *only when Convertible is selected.* BC7 should still be available for selection when Coupe is selected, but it should not have the engine appearance package requirement label or rule when Convertible is not selected.
    2. BCP
    3. BCS
    4. BC4
    5. B6P - Coupe only
    6. ZZ3 - Convertible only
    7. D3V - Coupe only
    8. SL9
    9. SLK - Coupe only
    10. SLN - Coupe only
    11. VUP - Coupe only

- ### Issue 10: Reorganize some of the exterior sections.
  - Wheels and Brake calipers can be combined into one section. Also include the Wheel Accessory section with them.
    - Display order:
      1. Wheels
      2. Brake Calipers
      3. Wheel Accessories
  - okay to move these option sections to different categories if needed for proper runtime display order.

- ### Issue 11: Seatbelts that are included with a 3LT interior need to act as default selections when one of those selections is made. The price rule is being accurately applied, but it needs to deselect 719 and make the corresponding seatbelt the selected option.
  - Example: 3LT_AUP_HAG was selected. It correctly made the 3A9 blue seatbelt $0 and added it to the 'auto added' list, but 719 also needs to be unselected. Do not make these selections concrete though, because the user can still choose another seatbelt, and the selection needs to override the 3A9 seatbelt if selected. All standard options that can be overridden by other selections should be removed from the selected options list. This will reduce confusion around what is actually selected and what is just included as a default until the user makes a different selection.

- ### Issue 12: R6X is a selectable option.
  - R6X should never be manually selectable by the user. It should only ever be auto-added when one of these interiors are selected:
    - HMO Jet Black/Sky Cool Gray
    - HVV Jet Black/Sky Cool Gray
    - HZB Sky Cool Gray/Jet Black
    - HVT Sky Cool Gray/Jet Black
    - HU0 Jet Black/Adrenaline Red
    - HXO Jet Black/Adrenaline Red
    - HUU Adrenaline Red/Jet Black
    - HZP Adrenaline Red/Jet Black
  - R6X price is already calculated in all of these interior options, so R6X does not need to exist on the front end as a selectable option. The D30 card should be the only option in color override section- shows disabled unless a color combination triggers it.
- Make sure that if D30 is triggered and R6X is also added, that the charge for D30 persists and R6X becomes $0.

### **Issue 13**: Interior selection still needs the full tiered display model.

Original reference: `debug/qa-3.md` Issue 2

Notes on the display model below:
- Keep all display fields consistent across all options in the interior section, even if some options only have one choice and do not need an expandable card. This will make the UI more consistent and easier to scan, and it will also future-proof the display in case more options are added later that do require the expandable card.
- Reduce collapsing/accordian levels where possible to keep ui as clean and understandable as possible.

**-Interior color reorganization**
  - 1LT
    - AQ9 GT1 Bucket Seats
      - HTA Jet Black
      - HUP Sky Cool Gray
      - HUQ Adrenaline Red
    - AE4 Competition Seats
      - HTJ Jet Black
  - 2LT
    - AQ9 GT1 Bucket Seats
      - Jet Black - This option should have an indicator showing that it has additional options available within it.
        - Jet Black
        - Jet Black with Yellow Stitching
        - Jet Black with Blue Stitching
        - Jet Black with Red Stitching
      - Sky Cool Gray - No expandable options, so standard option card with just the one choice.
      - Adrenaline Red - No expandable options
      - Natural - No expandable options
    - AH2 GT2 Bucket Seats
      - Jet Black - This option (and the others in this section) should have an indicator showing that it has additional options available within it.
        - Napa leather seating surfaces with perforated inserts.
          - Jet Black
          - Jet Black with Yellow Stitching
          - Jet Black with Blue Stitching
          - Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Jet Black Suede
          - Jet Black Suede with Yellow Stitching
          - Jet Black Suede with Blue Stitching
          - Jet Black Suede with Red Stitching
      - Sky Cool Gray
        - Napa leather seating surfaces with perforated inserts.
          - Sky Cool Gray
          - Sky Cool Gray Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Sky Cool Gray Suede
          - Sky Cool Gray Suede Two Tone
      - Adrenaline Red
        - Napa leather seating surfaces with perforated inserts.
          - Adrenaline Red
          - Adrenaline Red Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Adrenaline Red Suede Two Tone
      - Natural
        - Napa leather seating surfaces with perforated inserts.
          - Natural
          - Natural Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Suede
          - Natural Suede Two Tone
    - AE4 Competition Seats
      - Jet Black - This option should have an indicator that it has additional options available within it.
        - Napa leather seating surfaces with perforated inserts.
          - Jet Black
          - Jet Black with Yellow Stitching
          - Jet Black with Blue Stitching
          - Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Jet Black Suede
          - Jet Black Suede with Yellow Stitching
          - Jet Black Suede with Blue Stitching
          - Jet Black Suede with Red Stitching
      - Sky Cool Gray
        - Napa leather seating surfaces with perforated inserts.
          - Sky Cool Gray
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Sky Cool Gray Suede
      - Adrenaline Red
        - Napa leather seating surfaces with perforated inserts.
          - Adrenaline Red
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Adrenaline Red Suede
      - Natural
        - Napa leather seating surfaces with perforated inserts.
          - Natural
          - Natural Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Suede
          - Natural Suede Two Tone
  - 3LT
    - AH2 GT2 Bucket Seats
      - Jet Black
        - Napa leather seating surfaces with perforated inserts.
          - Jet Black
          - Jet Black with Yellow Stitching
          - Jet Black with Blue Stitching
          - Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Jet Black Suede
          - Jet Black Suede with Yellow Stitching
          - Jet Black Suede with Blue Stitching
          - Jet Black Suede with Red Stitching
      - Sky Cool Gray
        - Napa leather seating surfaces with perforated inserts.
          - Sky Cool Gray
          - Sky Cool Gray Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Sky Cool Gray Suede
          - Sky Cool Gray Suede Two Tone
      - Adrenaline Red
        - Napa leather seating surfaces with perforated inserts.
          - Adrenaline Red
          - Adrenaline Red Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Adrenaline Red Suede Two Tone
      - Adrenaline Red Dipped (only one option, so no need for an expandable card)
          - Adrenaline Red Dipped
      - Natural
        - Napa leather seating surfaces with perforated inserts.
          - Natural
          - Natural Two Tone
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Suede
          - Natural Suede Two Tone
      - Natural Dipped
        - Napa leather seating surfaces with perforated inserts.
          - Natural Dipped
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Dipped Suede
      - Santorini Blue (only one option, so no need for an expandable card)
          - Santorini Blue
      - Habanero
        - Napa leather seating surfaces with perforated inserts.
          - Habanero
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Habanero Suede
      - Very Dark Atmosphere
        - Napa leather seating surfaces with perforated inserts.
          - Very Dark Atmosphere
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Very Dark Atmosphere Suede
      - Ultimate Suede Jet Black
        - Napa leather seating surfaces with perforated inserts.
          - Ultimate Suede Jet Black
          - Ultimate Suede Jet Black with Yellow Stitching
          - Ultimate Suede Jet Black with Blue Stitching
          - Ultimate Suede Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Ultimate Suede Jet Black suede
          - Ultimate Suede Jet Black suede with Yellow Stitching
          - Ultimate Suede Jet Black suede with Blue Stitching
          - Ultimate Suede Jet Black suede with Red Stitching
      - Asymmetrical Adrenaline Red / Jet Black (only one option, so no need for an expandable card)
          - Asymmetrical Adrenaline Red / Jet Black
      - Asymmetrical Santorini Blue / Jet Black (only one option, so no need for an expandable card)
          - Asymmetrical Santorini Blue / Jet Black
      - Custom Interior trim and seat combinations
        - Sky Cool Gray interior / Jet Black seats
          - Napa leather seating surfaces with perforated inserts.
            - Sky Cool Gray interior / Jet Black seats (HZB)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Sky Cool Gray interior / Jet Black seats Suede (HVT)
        - Jet Black interior / Sky Cool Gray seats
          - Napa leather seating surfaces with perforated inserts.
            - Jet Black interior / Sky Cool Gray seats (HVV)
            - Jet Black interior / Sky Cool Gray seats Two Tone (3LT_R6X_AH2_HVV_TU7)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Jet Black interior / Sky Cool Gray seats Suede (3LT_R6X_AH2_HMO_N26)
            - Jet Black interior / Sky Cool Gray seats Suede Two Tone (3LT_R6X_AH2_HMO_N26_TU7)
        - Adrenaline Red interior / Jet Black seats
          - Napa leather seating surfaces with perforated inserts.
            - Adrenaline Red interior / Jet Black seats (HUU)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Adrenaline Red interior / Jet Black seats Suede (HZP)
        - Jet Black interior / Adrenaline Red seats
          - Napa leather seating surfaces with perforated inserts.
            - Jet Black interior / Adrenaline Red seats (HXO)
            - Jet Black interior / Adrenaline Red seats Two Tone (3LT_R6X_AH2_HXO_TU7)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Jet Black interior / Adrenaline Red seats Suede HXO (3LT_R6X_AH2_HXO_N26_TU7)
    - AE4 Competition Seats
      - Jet Black
        - Napa leather seating surfaces with perforated inserts.
          - Jet Black
          - Jet Black with Yellow Stitching
          - Jet Black with Blue Stitching
          - Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Jet Black Suede
          - Jet Black Suede with Yellow Stitching
          - Jet Black Suede with Blue Stitching
          - Jet Black Suede with Red Stitching
      - Sky Cool Gray
        - Napa leather seating surfaces with perforated inserts.
          - Sky Cool Gray
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Sky Cool Gray Suede
      - Adrenaline Red
        - Napa leather seating surfaces with perforated inserts.
          - Adrenaline Red
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Adrenaline Red Suede
      - Adrenaline Red Dipped (only one option, so no need for an expandable card)
          - Adrenaline Red Dipped
      - Natural
        - Napa leather seating surfaces with perforated inserts.
          - Natural
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Suede
      - Natural Dipped
        - Napa leather seating surfaces with perforated inserts.
          - Natural Dipped
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Natural Dipped Suede
      - Santorini Blue (only one option, so no need for an expandable card)
          - Santorini Blue
      - Habanero
        - Napa leather seating surfaces with perforated inserts.
          - Habanero
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Habanero Suede
      - Very Dark Atmosphere
        - Napa leather seating surfaces with perforated inserts.
          - Very Dark Atmosphere
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Very Dark Atmosphere Suede
      - Ultimate Suede Jet Black
        - Napa leather seating surfaces with perforated inserts.
          - Ultimate Suede Jet Black
          - Ultimate Suede Jet Black with Yellow Stitching
          - Ultimate Suede Jet Black with Blue Stitching
          - Ultimate Suede Jet Black with Red Stitching
        - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
          - Ultimate Suede Jet Black
          - Ultimate Suede Jet Black with Yellow Stitching
          - Ultimate Suede Jet Black with Blue Stitching
          - Ultimate Suede Jet Black with Red Stitching
      - Asymmetrical Adrenaline Red / Jet Black (only one option, so no need for an expandable card)
          - Asymmetrical Adrenaline Red / Jet Black
      - Asymmetrical Santorini Blue / Jet Black (only one option, so no need for an expandable card)
          - Asymmetrical Santorini Blue / Jet Black
      - Custom Interior trim and seat combinations
        - Adrenaline Red interior / Jet Black seats
          - Napa leather seating surfaces with perforated inserts.
            - Adrenaline Red interior / Jet Black seats (HUU)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Adrenaline Red interior / Jet Black seats Suede (HZP)
        - Jet Black interior / Adrenaline Red seats
          - Napa leather seating surfaces with perforated inserts.
            - Jet Black interior / Adrenaline Red seats (HXO)
          - Sueded microfiber seat inserts and sueded microfiber wrapped steering wheel.
            - Jet Black interior / Adrenaline Red seats Suede HXO
    - AUP Assymetrical seats
      - Asymmetrical Santorini Blue / Jet Black
      - Asymmetrical Adrenaline Red / Jet Black
