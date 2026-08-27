const WORKSPACES = new Set([
  "overview", "sections", "options", "groups", "assets", "changes", "advanced",
]);

const ENTITY_TYPES = new Set([
  "option", "exclusive_group", "rule_group", "section", "rule", "asset",
]);

function text(value) {
  return String(value || "").trim();
}

export function parseNavigation(search, defaultModel = "stingray") {
  const params = new URLSearchParams(search || "");
  const model = text(params.get("model")) || defaultModel;
  const requestedWorkspace = text(params.get("workspace"));
  const workspace = WORKSPACES.has(requestedWorkspace) ? requestedWorkspace : "overview";
  const requestedType = text(params.get("type"));
  const requestedId = text(params.get("id"));
  const hasEntity = ENTITY_TYPES.has(requestedType) && Boolean(requestedId);
  return {
    model,
    workspace,
    type: hasEntity ? requestedType : "",
    id: hasEntity ? requestedId : "",
    query: text(params.get("query")),
  };
}

export function serializeNavigation(navigation) {
  const params = new URLSearchParams();
  params.set("model", text(navigation?.model) || "stingray");
  params.set("workspace", WORKSPACES.has(navigation?.workspace)
    ? navigation.workspace
    : "overview");
  if (ENTITY_TYPES.has(navigation?.type) && text(navigation?.id)) {
    params.set("type", navigation.type);
    params.set("id", text(navigation.id));
  }
  if (text(navigation?.query)) params.set("query", text(navigation.query));
  return `?${params.toString()}`;
}

export function navigationForDestination(current, destination) {
  let type = text(destination?.entity_type);
  let id = text(destination?.entity_id);
  if (type === "group") {
    const separator = id.indexOf(":");
    const groupType = separator < 0 ? "" : id.slice(0, separator);
    id = separator < 0 ? "" : id.slice(separator + 1);
    type = groupType === "exclusive"
      ? "exclusive_group"
      : groupType === "rule" ? "rule_group" : "";
  }
  return {
    ...current,
    workspace: WORKSPACES.has(destination?.workspace)
      ? destination.workspace
      : current.workspace,
    type: ENTITY_TYPES.has(type) && id ? type : "",
    id: ENTITY_TYPES.has(type) ? id : "",
  };
}
