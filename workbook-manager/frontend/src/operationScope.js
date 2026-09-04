// Ownership of one draft operation, derived the way the backend derives it
// (graph_operations._operation_model): a row that carries its own model_key
// owns the operation — including the wildcard "*" a shared copy row uses —
// and only rows without a model_key column fall back to the schema's model
// context. Sending the selected model for a "*" row would be refused by the
// mutation ownership guard ("model context does not match row model_key").
export function operationModelId(schema, row, modelKey) {
  const context = schema?.model_context;
  if (!context?.required) return "";
  if (context.source === "row_model_key") {
    const rowModel = row?.model_key;
    if (rowModel != null && String(rowModel).trim() !== "") return String(rowModel).trim();
  }
  return context.value || modelKey || "";
}
