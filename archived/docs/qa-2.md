# QA-2 Remaining Issues

These are the QA-1 issues from lines 1-60 that are not covered, or not fully covered, by the QA-1 output pasted on lines 61-86.

## Not Covered

### **Issue 1**: Need to fix duplicate text in names and descriptions for all options and make a decision on what fields to display and when.
Original reference: `debug/qa-1.md` line 44
Reason: The output explicitly says there was no mass copy rewrite for option names/descriptions beyond display-rule changes, and final copy decisions are still pending.
Example 1:
option_id: opt_ahe_001
Label: Seat adjuster, driver power bolster
Desctiption: driver power bolster
Issue: repeated text
Example 2:
option_id: opt_uqs_001
Label: Audio system feature
description: Bose Premium 10-speaker system
option_id: opt_uqh_001
Label: Audio system feature
description: Bose Performance Series Sound System with 14 speakers
Issue: Duplicate generic label makes description required for identification.
Example 3:
option_id: opt_aq9_001
label: GT1 Bucket Seats
description: GT1 bucket
issue: label and description are repetetive and label is more descriptive.


### **Issue 2**: Need to simplify the interior option display.
Original reference: `debug/qa-1.md` line 46
Expected: Interiors should be tiered by color, then material, then other options like two tone.
Reason: The output explicitly says the full color/material/two-tone tiering remains follow-up work.

## Partially Covered / Needs Follow-Up Verification

### **Issue 3**: Suspension needs to be a replaceable default.
Original reference: `debug/qa-1.md` lines 36-37
Expected: FE1 selected by default. When Z51 is selected, FE3 selected by default, FE4 available, FE1 and FE2 unavailable.
Covered by output: Browser smoke verified that Z51 removes FE1.
Remaining gap: The output does not claim FE1 default state, FE3 default selection, FE4 availability, or FE2 unavailability.

### **Issue 4**: Exhaust needs to be a replaceable default.
Original reference: `debug/qa-1.md` lines 39-40
Expected: NGA selected by default. Stay selected when WUB is selected, but NGA should be unselected if NWI is selected.
Remaining gap: The output does not claim or verify NGA default selection.

### **Issue 5**: Inactive options with label "Display only source row" need the label to say why they are inactive and what option they require.
Original reference: `debug/qa-1.md` lines 31-34
Covered by output: BC7 was consolidated and unavailable/inactive rows were hidden.
Remaining gap: The output does not claim a general disabled-state label fix for display-only rows that remain visible in other cases. Some fields are set up with the correct "Requires [option]" label but the text just happened to line up already so need to figure out where the label is built from.

# QA-2 New Issues

### **Issue**: Coupe should be display_order:1 , convertible display_order: 2.

### **Issue**: Body and trim level should not auto advance- they should require the user to initiate the next button.

### **Issue**: Don't list the entire list of standard equipment below the trim levels because it is overwhelming and not helpful to customers.
Expected: The standard equipment should be listed under the first section selections broken up into categories as it is now to make it easier to read. The equipment group equipment should be displayed below the trim level options in that section, expanding 1lt trim level default, and when 2lt or 3lt is selected, that equipment group expands and the other two are collapsed. This way, customers can easily see what is included with each trim without being overwhelmed by a long list of equipment that may not be relevant to their selection.

### **Issue**: The summary export does not need to include all of the standard and included equipment. The list of what should be included is all selected options, included options...and maybe there should be a flag on what options should be included in the summary. I may add that to the workbook and then it can be added to the export and the UI display.

### **Issue**: single select options in sections that are not required need to be able to be unselected. Example: ZYC in spoiler section.

### **Issue**: The custom stitch section should be removed completely because the options overlap with the options that auto apply and are selected in the base interior section. Color override could stay but they should be inactive unless they are triggered by the corresponding color selection in the interior color section.

### **Issue**: UQT should only show as an option on 1LT coupe or convertible. It is included equipment otherwise so does not need to be in the selectable options list for the other trims.

### **Issue**: The LPO options that change to $0 when the package is selected should be in selected state. Example: When PDY is selected, the RYT and S08 options add to the 'auto added options' list and everything, which is correct. The issue is that they are still selectable in that state and add to the 'selected options' list which just adds redundancy. Since they are included when the package is selected, they should be in a selected state but not selectable to be unselected. This is a case where the same option needs to be available in multiple states and the rules should just override the default selection and availability when the corresponding options are selected. This is similar to the T0A/Z51 case mentioned in the QA-1 issues.

