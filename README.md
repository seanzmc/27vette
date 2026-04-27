# 2027 Corvette Stingray Order Form

Static customer order-form app for configuring a 2027 Corvette Stingray and exporting the completed submission.

## App

The runtime app lives in `form-app/`:

- `index.html` - page shell and summary layout
- `styles.css` - app styling
- `app.js` - form behavior, validation display, summary, and export logic
- `data.js` - embedded Stingray form data used by the app

The app runs without a build step or package install.

## Run Locally

Open `form-app/index.html` directly in a browser, or serve the folder with a simple static server:

```sh
cd form-app
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Submission Exports

Use the top-right export buttons:

- `Export JSON` downloads the order payload, including customer information, selected options, auto-added RPOs, open requirements, and pricing.
- `Export CSV` downloads a tabular version of the submission. Customer name, address, email, phone number, and comments are included as customer rows before the selected line items.

The customer information form is its own final form step and is included in final submission exports.

## Archived Materials

Planning, development, workbook, generated-output, and source-transformation materials were moved into `archived/` so the root stays focused on the deliverable app.

Archived contents include:

- `PLAN.md`
- `Rule_Mapping.csv`
- `corvette-build/`
- `corvette-contract/`
- `corvette-ingest/`
- `form-output/`
- `fusion-plan/`
- `referenceSheets/`
- `scripts/`
- `stingray_master.xlsx`

These files are retained for traceability, but they are not required to run the static app.
