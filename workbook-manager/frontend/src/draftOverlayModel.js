// Checkpoint 2C pure helpers for rendering the backend draft overlay.
//
// The backend adapter (workbook-manager/backend/app/draft_overlay.py) owns the
// overlay shape: state, operation identity, base, proposed, effective,
// changed_fields, direct_impact, conflicts. These helpers only read that shape
// so every connected surface presents authored and proposed values the same
// way. Nothing here re-derives a diff, decides product behavior, or patches a
// heading independently of the adapter.

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

export const ACTIVE_OVERLAY_STATES = new Set([
  "modified", "added", "pending_deletion", "conflicted",
]);

export function hasDraftOverlay(overlay) {
  return Boolean(overlay && ACTIVE_OVERLAY_STATES.has(overlay.state));
}

export function overlayStateLabel(overlay) {
  switch (overlay?.state) {
    case "modified": return "Draft modified";
    case "added": return "Draft added";
    case "pending_deletion": return "Draft deletion pending";
    case "conflicted": return "Draft blocked";
    default: return "";
  }
}

// The value a reviewer should read for `field`: the proposed effective value
// when the draft changes it, otherwise the authored value. A pending delete and
// a conflicted overlay never replace the authored value (EFFECTIVE-02/04).
export function effectiveValue(overlay, field, authored) {
  if (!overlay || (overlay.state !== "modified" && overlay.state !== "added")) {
    return authored;
  }
  const effective = overlay.effective;
  if (!effective || !Object.hasOwn(effective, field)) return authored;
  return effective[field];
}

// Before/after for one field when the draft changes it; null otherwise. Lets a
// heading or fact chip show "authored → proposed" without re-diffing rows.
export function fieldChange(overlay, field) {
  const pair = overlay?.changed_fields?.[field];
  if (!pair) return null;
  return { before: pair.before ?? null, after: pair.after ?? null };
}

// A section node's heading lives in the owning table's name field:
// context-section edits change `section_name`, section-presentation edits
// change `display_label`. Reads the overlay's own operation identity, so a
// membership-only overlay (a child-row op) still resolves to display_label and
// falls back to the authored heading.
export function sectionHeadingField(overlay) {
  return overlay?.operation?.table_name === "context_sections"
    ? "section_name"
    : "display_label";
}

export function changedFieldEntries(overlay) {
  return Object.entries(overlay?.changed_fields || {}).map(([field, pair]) => ({
    field,
    before: pair?.before ?? null,
    after: pair?.after ?? null,
  }));
}

// Exact reason a conflicted overlay blocks mutation; "" when not blocked.
export function overlayBlockReason(overlay) {
  if (overlay?.state !== "conflicted") return "";
  const messages = (overlay.conflicts || []).map((conflict) => text(conflict.message)).filter(Boolean);
  return messages.join(" ") || "Draft intent is not bound to the current editable projection.";
}

export function operationLabel(overlay) {
  const operation = overlay?.operation;
  if (!operation) return "";
  return `operation ${operation.id} · ${text(operation.action)} · ${text(operation.table_name)}`;
}

const STATE_BY_ACTION = { update: "modified", add: "added", delete: "pending_deletion" };

// Project a durable operation (the POST /api/drafts/{id}/operations response)
// into the same overlay shape the backend adapter emits, so an editor's
// post-Save panel and the connected detail render through one component. The
// draft's binding was just validated by that save, so no conflicts apply here.
export function operationOverlay(operation, directImpact = null) {
  if (!operation) {
    return {
      draft_id: "", draft_revision: 0, state: "unchanged", operation: null,
      base: null, proposed: null, effective: null, changed_fields: {},
      direct_impact: null, conflicts: [],
    };
  }
  const action = text(operation.action);
  return {
    draft_id: text(operation.draft_id),
    draft_revision: Number(operation.id) || 0,
    state: STATE_BY_ACTION[action] || "modified",
    operation: {
      id: operation.id,
      action,
      table_name: text(operation.table_name),
      family: text(operation.family),
      model_id: text(operation.model_id),
      source_sheet: text(operation.source_sheet),
      source_row: operation.source_row ?? null,
      physical_key: text(operation.physical_key),
      entity_key: operation.entity_key || {},
    },
    base: operation.original ?? null,
    proposed: operation.final ?? null,
    effective: action === "delete" ? null : operation.final ?? null,
    changed_fields: operation.changed_fields || {},
    direct_impact: directImpact,
    conflicts: [],
  };
}
