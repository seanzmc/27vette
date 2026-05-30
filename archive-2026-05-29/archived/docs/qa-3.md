# QA-3 Remaining Issues

These are the `debug/qa-2.md` items that remain unresolved, or need follow-up verification, after the QA-2 implementation pass.

## Not Covered

### **Issue 1**: Need to fix duplicate text in names and descriptions for all options and make a decision on what fields to display and when.
Original reference: `debug/qa-2.md` lines 7-27
Reason: The QA-2 pass did not include a mass option copy rewrite or a final display-field decision.

Examples from QA-2:

- `opt_ahe_001`
  - Label: Seat adjuster, driver power bolster
  - Description: driver power bolster
  - Issue: repeated text
- `opt_uqs_001`
  - Label: Audio system feature
  - Description: Bose Premium 10-speaker system
- `opt_uqh_001`
  - Label: Audio system feature
  - Description: Bose Performance Series Sound System with 14 speakers
  - Issue: duplicate generic label makes description required for identification.
- `opt_aq9_001`
  - Label: GT1 Bucket Seats
  - Description: GT1 bucket
  - Issue: label and description are repetitive and label is more descriptive.

### **Issue 2**: Need to simplify the interior option display.
Original reference: `debug/qa-2.md` lines 30-33
Expected: Interiors should be tiered by color, then material, then other options like two tone.
Reason: The QA-2 pass removed Custom Stitch from selectable runtime output, but did not implement the full color/material/two-tone tiered interior selection redesign.

### **Issue 3**: Add a summary/export inclusion flag if the workbook contract gets one.
Original reference: `debug/qa-2.md` line 62
Current state: The QA-2 pass removed the full standard/included equipment dump from the JSON export.
Remaining gap: There is still no workbook-driven flag for which selected/included options should appear in the summary/export. This should wait until the workbook adds an explicit field.

### **Issue 4**: Color Override options should be inactive unless triggered by the corresponding interior color selection.
Original reference: `debug/qa-2.md` line 66
Current state: The QA-2 pass removed the Custom Stitch section from selectable runtime output.
Remaining gap: Color Override stayed in the UI, but it still needs a full rule pass so override options are inactive unless triggered by the matching interior/color condition.

## Needs Follow-Up Verification

### **Issue 5**: Display-only inactive labels should explain the actual requirement when possible.
Original reference: `debug/qa-2.md` lines 48-51
Current state: The QA-2 pass moved the generic `Display-only source row` fallback after rule-based disabled reasons, so rule-backed rows can show `Requires...` or `Blocked by...` first.
Remaining gap: This still needs a full UI/data audit for any remaining visible display-only rows that fall back to the generic label.

## New Issues

BC7 should be selected by default when coupe is selected.

5V7 rules need fixed. Should be available when 5ZZ or 5ZU is selected, currently shows only available with 5ZU.

Section 8 should go exhaust, spoiler, then stripes, then lpo exterior, lpo wheels, and then wheel accessories.

going from a long section to a short section should reset the section scroll to the top, currently it stays at the same scroll position which can be confusing.

seat prices need to be subtracted from the base interior color prices that are displayed. Currently double charging for seats.

D30 should not be selectable by the user. It should only be active when a color combination triggers it.
