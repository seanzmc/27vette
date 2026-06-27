Feasible. Not too much overhead if we keep it generic and workbook-owned.

    Current evidence:
    - form-app/app.js already renders images on context cards if a contextChoice row has image_url.
      - renderContextCard() calls renderCardMedia(choice, ...).
      - renderCardMedia() uses image_url, image_alt, image_fit, image_position.
    - CSS already has .choice-media card image styling.
    - Gap: the generators currently do not emit image fields for body-style context choices.
    - asset_map currently supports only:
      - image_url
      - image_alt
      - image_fit
      - image_position
    - asset_map currently has model-card image rows, but no body-style/context-choice image rows.

    Feasibility by option:

    1. Single image on Coupe / Convertible cards
    - Feasibility: low risk, simple.
    - Existing runtime image renderer can probably be reused with little/no runtime change.
    - Work needed:
      - Add asset_map rows for body-style choices.
      - Teach generators to merge those assets into contextChoices.
      - Add generated-data/runtime tests.
    - This is the cleanest first pass.

    2. Default image plus hover image
    - Feasibility: moderate, still reasonable.
    - Extra work because the workbook schema and runtime need a new hover image field.
    - Main caveat: hover has limited/no meaning on mobile/touch. The base image must still be the correct customer-facing image. Hover should be enhancement only.
    - Work needed:
      - Add hover fields to asset_map, likely:
        - hover_image_url
        - hover_image_alt
        - optionally hover_image_position
      - Emit those into generated contextChoices.
      - Update renderCardMedia() to render a second image layer when hover data exists.
      - CSS crossfade on .choice-card:hover and .choice-card:focus-visible.
      - On touch/mobile, show the base image only unless we intentionally add tap/focus behavior.

    My recommendation:
    - Do the hover-capable structure, but keep it optional.
    - That means:
      - If only image_url exists, single-image cards work.
      - If hover_image_url exists, the card crossfades on hover/focus.
    - This avoids doing single-image now and reworking the same path later.

    Simple implementation plan:

    Pass 1: workbook/generator/runtime substrate
    1. Extend asset_map headers:
       - hover_image_url
       - hover_image_alt
       - hover_image_position
    2. Add active body-style rows, probably target type:
       - target_type=context_choice
       - target_id=body_style__coupe
       - target_id=body_style__convertible
    3. Decide scope:
       - If the same coupe/convertible images are valid for all models, use one row per model or update the loader to allow model_key=*.
       - Current load_asset_map() only matches exact model_key, so the lowest-risk pass is one row per active model: stingray, grand_sport, z06.
    4. Update generators:
       - scripts/generate_stingray_form.py
       - scripts/corvette_form_generator/inspection.py
       - Merge context-choice asset rows into body-style contextChoices.
       - Include image fields in generated form_context_choices, draft/preview JSON, and form-app/data.js.
    5. Update runtime:
       - Keep renderContextCard() generic.
       - Update renderCardMedia() to render a hover image only when hover_image_url exists.
       - Add CSS opacity transition, no layout shift.
    6. Tests:
       - Generated data: body-style context choices include base/hover image fields.
       - Runtime: renderContextCard() emits media and hover image markup.
       - Multi-model: Stingray/Grand Sport/Z06 body-style cards still render and remain selectable.
    7. Browser smoke:
       - Open local app.
       - Switch models.
       - Verify Coupe/Convertible cards show images.
       - Verify hover crossfade on desktop.
       - Verify mobile/touch does not depend on hover.
       - Check console errors.

    Validation gates:
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    - .venv/bin/python scripts/generate_z06_form.py
    - .venv/bin/python scripts/generate_grand_sport_form.py
    - .venv/bin/python scripts/generate_stingray_form.py
    - node --test tests/stingray-generator-stability.test.mjs
    - node --test tests/z06-form-data-draft.test.mjs
    - node --test tests/grand-sport-draft-data.test.mjs
    - node --test tests/multi-model-runtime-switching.test.mjs
    - node --test tests/stingray-form-regression.test.mjs

    Bottom line:
    - Single image: definitely worth doing, low overhead.
    - Hover image: feasible and not excessive if implemented generically as optional generated metadata.
    - I would not hardcode hover URLs in app.js. Put the URLs in asset_map, emit them, and let runtime render whatever the data provides.
