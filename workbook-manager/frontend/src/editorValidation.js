function fieldLabel(column) {
  return column.control?.label || column.label || String(column.name || "")
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}

export function validateField(column, value, referenceState = {}) {
  const control = column.control;
  const label = fieldLabel(column);
  const text = value == null ? "" : String(value).trim();

  if (!control) return `${label} has no registered editor control.`;
  if (!text && ["forbidden", "never_blank_key"].includes(control.blank)) {
    return `${label} is required.`;
  }
  if (!text) return "";

  if (["boolean", "finite"].includes(control.kind) && !control.values.includes(value)) {
    return `Choose ${label} from the accepted values: ${control.values.join(", ")}.`;
  }
  if (control.kind === "reference") {
    if (referenceState.loading) return `${label} choices are still loading.`;
    if (referenceState.error) {
      return `${label} choices are unavailable: ${referenceState.error}`;
    }
    const values = (referenceState.options || []).map((option) => String(option.value));
    if (referenceState.loaded && !values.includes(String(value))) {
      return `Current value is not valid for this field. Choose an available ${label}.`;
    }
  }
  if (control.kind === "integer" || control.kind === "money") {
    const number = Number(text);
    if (!Number.isFinite(number) || !Number.isInteger(number)) {
      return `${label} must be a whole number.`;
    }
    if (control.min != null && number < control.min) {
      return `${label} must be at least ${control.min}.`;
    }
    if (control.max != null && number > control.max) {
      return `${label} must be no more than ${control.max}.`;
    }
  }
  if (control.kind === "url") {
    try {
      const parsed = new URL(text);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error("protocol");
    } catch {
      return `${label} must be a complete http or https URL.`;
    }
  }
  return "";
}

export function validateDraft(schema, draft, referenceStates = {}) {
  const errors = {};
  for (const column of schema.columns) {
    const error = validateField(
      column,
      draft[column.name],
      referenceStates[column.name],
    );
    if (error) errors[column.name] = error;
  }
  return errors;
}

function normalizedValue(value) {
  return value == null ? "" : String(value);
}

export function isDraftDirty(schema, initial, draft) {
  return schema.columns.some(
    (column) => normalizedValue(initial?.[column.name]) !== normalizedValue(draft[column.name]),
  );
}
