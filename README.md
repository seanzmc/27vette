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

## Active Workflow Materials

The current workbook-to-app workflow lives at the project root:

- `stingray_master.xlsx` - active Stingray source workbook and generated `form_*` sheets
- `scripts/generate_stingray_form.py` - regenerates workbook form sheets, `form-output/`, and `form-app/data.js`
- `form-output/` - generated JSON and CSV contract exports used for inspection and handoff

### Workbook Generator Setup

Use a project-local Python environment before running the workbook generator:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
```

## Archived Materials

Deprecated planning, skill, reference, and source-transformation materials live in `archived/`.

Archived contents include:

- `PLAN.md`
- `Rule_Mapping.csv`
- `$skills/`
- `corvette-contract/`
- `fusion-plan/`
- `referenceSheets/`

These files are retained for traceability, but they are not required to run the static app.
