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

### **Issue 2**: Interior selection still needs the full tiered display model.

Original reference: `debug/qa-3.md` Issue 2

Current state:

- The last pass fixed double-charged seat prices by subtracting the selected seat price from displayed and exported base interior pricing.
- The UI still renders base interiors as one filtered choice grid after seat selection.

Remaining gap:

- Interiors should be simplified into a tiered selection flow:
  - color
  - material
  - other options, such as two-tone

Needed fix:

- Build a clearer interior model from the workbook data instead of presenting every valid base interior row as a flat card list.
- Preserve the corrected seat-price subtraction while changing the interior display structure.

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
