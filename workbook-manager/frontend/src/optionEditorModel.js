// Checkpoint 3D derivation helpers for the connected option editor.
//
// Pure functions only: the React component wires these to the shared
// EditorShell/RecordForm surfaces. Everything here is derived from the
// connected option detail (`GET /api/explorer/{model}/options/{id}`), the
// registry-owned table schema (`GET /api/records/options/schema`), and the
// durable draft operations — no product knowledge lives in this module.

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

// Editable fields come from the registry schema's column list, never a local
// copy: RecordForm renders and submits every schema column, and
// drafts.save_operation overlays every submitted value onto the coalesced
// draft operation. A local field list here could go stale when the registry
// adds or renames an option column, leaving that column initialized to ""
// and erasing workbook-authored data on an unrelated save.
export function initialDraftFromDetail(detail, schema) {
  const option = detail?.option || {};
  const draft = {};
  for (const column of schema?.columns || []) {
    draft[column.name] = text(option[column.name]);
  }
  const target = editorTarget(detail);
  return {
    draft,
    target,
    label: entityLabel(detail),
    lineage: target.lineage,
  };
}

// Overlay the effective draft state of this physical row (if any) onto the
// projected values, so reopening the editor — or choosing "Keep editing"
// after a save — seeds from the coalesced operation instead of from the
// untouched projection. Otherwise a second save would resubmit projected
// values and silently revert previously drafted fields. NULL and blank
// entries keep the projected value: blank renders as "not specified /
// inherit", which is identical presentation for both states.
export function applyDraftOverlay(draft, operation) {
  const final = operation?.final;
  if (!final || typeof final !== "object") return draft;
  const seeded = { ...draft };
  for (const name of Object.keys(seeded)) {
    const value = final[name];
    if (value !== null && value !== undefined && String(value) !== "") {
      seeded[name] = String(value);
    }
  }
  return seeded;
}

// Latest durable operation bound to this exact physical row, matched by the
// same identity drafts.save_operation uses (source_sheet + physical_key).
export function matchingDraftOperation(operations, target) {
  const sheet = target?.lineage?.source_sheet || "";
  const physicalKey = target?.lineage?.physical_key || "";
  const rows = Array.isArray(operations) ? operations : [];
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const operation = rows[index];
    if (
      (operation?.source_sheet || "") === sheet &&
      (operation?.physical_key || "") === physicalKey
    ) {
      return operation;
    }
  }
  return null;
}

export function editorTarget(detail) {
  const option = detail?.option || {};
  return {
    table: "options",
    key: { option_id: text(option.option_id) },
    model_id: text(detail?.model_key),
    lineage: {
      source_sheet: text(option.src_sheet),
      source_row: option.src_row ?? null,
      physical_key: text(option.physical_key),
    },
  };
}

export function entityLabel(detail) {
  const option = detail?.option || {};
  const parts = [text(option.rpo).trim(), text(
    option.option_name || option.name,
  ).trim()].filter(Boolean);
  return parts.length ? parts.join(" — ") : text(option.option_id) || "Option";
}

export function relationshipImpact(detail) {
  return {
    availability: (detail?.availability || []).length,
    groups:
      (detail?.exclusive_groups || []).length +
      (detail?.rule_groups || []).length,
    rules: (detail?.rules || []).length,
    pricingRules: (detail?.pricing || []).length,
    variantOverrides: (detail?.variant_overrides || []).length,
    defaultRules: (detail?.default_rules || []).length,
    images: (detail?.assets || []).length,
  };
}
