const OVS_STATUSES = new Set(["standard", "available", "unavailable"]);

export function optionCreationPlan(optionOperation, activeVariants, statuses) {
  const missing = activeVariants
    .map((variant) => String(variant.variant_id))
    .filter((variantId) => !OVS_STATUSES.has(String(statuses?.[variantId] || "")));
  if (missing.length) {
    return { complete: false, missing_variant_ids: missing, operations: [] };
  }
  const optionId = String(optionOperation?.key?.option_id || "");
  const operations = [optionOperation, ...activeVariants.map((variant) => {
    const variantId = String(variant.variant_id);
    return {
      table: "option_availability",
      model_id: optionOperation.model_id,
      op: "add",
      key: { option_id: optionId, variant_id: variantId },
      record: {
        option_id: optionId,
        variant_id: variantId,
        status: statuses[variantId],
      },
    };
  })];
  return { complete: true, missing_variant_ids: [], operations };
}

export function dependencyDeletionOperations(root, dependents, selections) {
  const missing = dependents
    .map((_, index) => String(index))
    .filter((index) => !["delete", "deactivate"].includes(selections?.[index]));
  if (missing.length) {
    return { complete: false, missing_indices: missing, operations: [] };
  }
  const operations = dependents.map((dependent, index) => {
    const action = selections[String(index)];
    return {
      table: dependent.table,
      model_id: dependent.model_id || "",
      op: action === "deactivate" ? "update" : "delete",
      key: dependent.entity_key,
      ...(action === "deactivate" ? { record: { active: "False" } } : {}),
    };
  });
  operations.push({
    table: root.table,
    model_id: root.model_id || "",
    op: "delete",
    key: root.key,
  });
  return { complete: true, missing_indices: [], operations };
}
