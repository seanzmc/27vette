# App Refresh Workflow

Use this checklist whenever `stingray_master.xlsx` changes and the static app needs the updated workbook content.

## Scope

Source of truth:

- `stingray_master.xlsx`

Generated app artifacts:

- `form-app/data.js`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- Generated `form_*` sheets inside `stingray_master.xlsx`

Frontend runtime files that usually should not change during a data refresh:

- `form-app/index.html`
- `form-app/app.js`
- `form-app/styles.css`

## 1. Confirm the Workbook Edit

Before regenerating app data, confirm the workbook change is actually saved on disk.

For text/table edits, reopen `stingray_master.xlsx` and spot-check the edited sheet and cells. Do not rely only on a script saying it saved successfully.

Also check the working tree so generated changes do not get mixed with unrelated files:

```sh
cd /Users/seandm/Projects/27vette
git status --short
```

If temporary backups exist, keep them out of the final commit unless they are intentionally part of the handoff.

## 2. Regenerate App Data

Run the generator from the project root:

```sh
cd /Users/seandm/Projects/27vette
python3 scripts/generate_stingray_form.py
```

Expected behavior:

- Reads `stingray_master.xlsx`
- Rebuilds generated `form_*` sheets in the workbook
- Writes `form-output/stingray-form-data.json`
- Writes `form-output/stingray-form-data.csv`
- Writes `form-app/data.js`
- Prints counts for choices, context choices, standard equipment, rules, price rules, interiors, and validation errors

If `validation_errors` is greater than `0`, stop and inspect the generator output before pushing.

## 3. Verify Generated Data

Run the regression suite:

```sh
cd /Users/seandm/Projects/27vette
node --test tests/stingray-form-regression.test.mjs
```

Then spot-check the generated timestamp:

```sh
rg -n '"generated_at"' form-app/data.js form-output/stingray-form-data.json
```

For copy-only workbook updates, also search for representative changed labels or descriptions:

```sh
rg -n "Exact changed text here" form-app/data.js form-output/stingray-form-data.json
```

## 4. Manually Verify the Static App

Serve the static app:

```sh
cd /Users/seandm/Projects/27vette/form-app
python3 -m http.server 8000
```

Open `http://localhost:8000`.

Manual checks:

- Hard refresh or cache-bust if the UI appears stale.
- Confirm the edited workbook text appears in the relevant option cards or standard/included equipment surfaces.
- Walk through body style and trim selection if the changed rows vary by variant.
- Confirm no unrelated app layout or behavior changed.

Stop the local server after verification.

## 5. Review the Diff

Return to the project root:

```sh
cd /Users/seandm/Projects/27vette
git status --short
git diff --stat
```

Expected files for a normal workbook-to-app refresh:

- `stingray_master.xlsx`
- `form-app/data.js`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`

Possible but not automatically expected:

- `README.md` or workflow docs, only when process documentation changed
- `tests/stingray-form-regression.test.mjs`, only when the app contract changed

Do not stage temporary workbook backups, lock files, or unrelated untracked files.

## 6. Commit and Push

Stage only the intended files:

```sh
git add stingray_master.xlsx form-app/data.js form-output/stingray-form-data.json form-output/stingray-form-data.csv
```

If this workflow doc changed, include it explicitly:

```sh
git add App-refresh-workflow.md
```

Commit with a data-refresh message:

```sh
git commit -m "Refresh Stingray app data"
```

Push the branch:

```sh
git push
```

## Handoff Checklist

Report these items after each refresh:

- Workbook change verified on disk: yes/no
- Generator completed: yes/no, include `validation_errors`
- Regression test result: pass/fail
- Manual app check: pass/fail or pending
- Files staged/committed/pushed
- Any excluded files, such as backups or unrelated untracked files
