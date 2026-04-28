# App refresh workflow:

1. Regenerate the app data from the updated workbook:

```sh
cd /Users/seandm/Projects/27vette
python3 scripts/generate_stingray_form.py
```

That script reads `stingray_master.xlsx`, rewrites the generated `form_*` sheets in the workbook, refreshes `form-output/stingray-form-data.json`, refreshes `form-output/stingray-form-data.csv`, and updates `form-app/data.js`, which is what the frontend actually loads.

2. Validate generated output:

```sh
node --test tests/stingray-form-regression.test.mjs
```

Also spot-check that `form-app/data.js` has a new `dataset.generated_at` timestamp and that corrected copy appears in `choices` / `standardEquipment`.

3. Manually verify the static app:

```sh
cd /Users/seandm/Projects/27vette/form-app
python3 -m http.server 8000
```

Open `http://localhost:8000`, hard refresh/cache bust if needed, then spot-check the edited labels/descriptions in the relevant option cards and standard/included equipment surfaces.

4. Commit/push the intended files.

Likely files to include:
- `stingray_master.xlsx`
- `form-app/data.js`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`

Do not include unless you intentionally want it tracked:
- `stingray_master.backup-before-de-copy-cleanup-20260428.xlsx`

Current unrelated untracked file also exists:
- `archived/Int-reorg.md`

The frontend has no build step; pushing the regenerated static data is the handoff to the app.
