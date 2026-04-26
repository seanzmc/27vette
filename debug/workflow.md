For **options data**, edit the **spreadsheet/source workbook**, then regenerate `data.js`.

Treat `form-app/data.js` as a generated deploy artifact. Manual edits there are fine only for an emergency hotfix, but they create drift: the next workbook export/regeneration can overwrite them, and you lose the audit trail for why a price/rule/availability changed.

Use this split:

- **Spreadsheet/workbook:** option labels, RPOs, prices, availability, body/trim applicability, standard/included equipment, rule relationships, interior data.
- **`form-app/app.js`:** behavior bugs, validation logic, submission/export logic, how choices react.
- **`form-app/styles.css`:** visual/layout fixes.
- **`form-app/index.html`:** page structure, buttons, customer fields, containers.

For your first QA pass, I’d capture notes like:

```text
Issue:
Step/body/trim:
Selected options:
Expected:
Actual:
Screenshot:
Data issue or visual issue:
```

Then we can batch them cleanly: data corrections go back to the workbook, visual fixes go to CSS, and logic fixes go to `app.js`.

No files changed here; no gates run.

```text
Issue:
Step/body/trim:
Selected options:
Expected:
Actual:
Screenshot:
Data issue or visual issue:
```
