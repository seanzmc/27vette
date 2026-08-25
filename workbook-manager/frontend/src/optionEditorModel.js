// Checkpoint 3D derivation helpers for the connected option editor.
//
// Pure functions only: the React component wires these to the shared
// EditorShell/RecordForm surfaces. Everything here is derived from the
// connected option detail (`GET /api/explorer/{model}/options/{id}`) and from
// registry-owned schema controls — no product knowledge lives in this module.

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

// The projected option fields the option editor edits, in §10.6 group order.
// Identity (option_id) is locked on edit; everything else renders through the
// schema's registry control kinds.
export const OPTION_FIELD_ORDER = [
  "option_id",
  "rpo",
  "price",
  "option_name",
  "description",
  "detail_raw",
  "section_id",
  "selectable",
  "display_order",
  "display_behavior",
  "active",
];

export function initialDraftFromDetail(detail) {
  const option = detail?.option || {};
  const draft = {};
  for (const name of OPTION_FIELD_ORDER) {
    draft[name] = text(option[name]);
  }
  const target = editorTarget(detail);
  return {
    draft,
    target,
    label: entityLabel(detail),
    lineage: target.lineage,
  };
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
