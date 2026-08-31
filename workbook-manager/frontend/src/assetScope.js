export const ALL_MODELS = "*";

export function reconciliationModel(modelKey) {
  return modelKey === ALL_MODELS ? "" : modelKey;
}

export function assetInScope(item, modelKey) {
  if (!item) return false;
  return modelKey === ALL_MODELS || item.model_key === modelKey;
}

export function assignmentTargetsInScope(targets, modelKey) {
  return modelKey === ALL_MODELS
    ? targets
    : targets.filter((target) => target.model_key === modelKey);
}
