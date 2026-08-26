// Checkpoint 3E pure derivations for contextual group/member editing.
//
// React supplies the connected group read, registry schemas, bounded reference
// labels, and durable draft operations. This module contains no product rules,
// group-family switch, or alternate write contract.

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function numberOrder(value, fallback) {
  if (value === null || value === undefined || String(value).trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function config(detail) {
  const editor = detail?.editor || {};
  return {
    groupTable: text(editor.group_table),
    groupIdField: text(editor.group_id_field),
    memberTable: text(editor.member_table),
    memberIdField: text(editor.member_id_field),
    memberGroupField: text(editor.member_group_field),
    memberOrderField: text(editor.member_order_field),
    memberActiveField: text(editor.member_active_field),
    groupId: text(detail?.group_id),
    modelId: text(detail?.model_key),
  };
}

export function initialGroupDraft(detail, schema) {
  const group = detail?.group || {};
  const draft = {};
  for (const column of schema?.columns || []) {
    draft[column.name] = text(group[column.name]);
  }
  const editor = config(detail);
  return {
    draft,
    target: {
      table: editor.groupTable,
      model_id: editor.modelId,
      key: { [editor.groupIdField]: editor.groupId },
    },
    member_table: editor.memberTable,
    member_id_field: editor.memberIdField,
    member_group_field: editor.memberGroupField,
    member_order_field: editor.memberOrderField,
    member_active_field: editor.memberActiveField,
  };
}

export function matchingGroupOperation(operations, detail) {
  const editor = config(detail);
  const sheet = text(detail?.group?.src_sheet);
  const physicalKey = text(detail?.group?.physical_key);
  const rows = Array.isArray(operations) ? operations : [];
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const operation = rows[index];
    if (
      operation?.table_name === editor.groupTable &&
      text(operation?.source_sheet) === sheet &&
      text(operation?.physical_key) === physicalKey
    ) {
      return operation;
    }
  }
  return null;
}

export function applyGroupDraftOverlay(draft, operation) {
  if (!operation?.final || typeof operation.final !== "object") return draft;
  const seeded = { ...draft };
  for (const name of Object.keys(seeded)) {
    if (Object.hasOwn(operation.final, name)) seeded[name] = text(operation.final[name]);
  }
  return seeded;
}

function memberLabel(row, memberId, labels) {
  const direct = text(labels?.[memberId]).trim();
  if (direct) return direct;
  const rpo = text(row?.rpo).trim();
  const name = text(row?.option_name || row?.name).trim();
  return [rpo, name].filter(Boolean).join(" — ") || memberId;
}

function memberRecord(row, editor, labels, fallbackOrder) {
  const memberId = text(row?.[editor.memberIdField]);
  return {
    ...row,
    [editor.memberGroupField]: editor.groupId,
    [editor.memberIdField]: memberId,
    member_id: memberId,
    display_order: numberOrder(row?.[editor.memberOrderField], fallbackOrder),
    active: row?.[editor.memberActiveField] ?? "True",
    label: memberLabel(row, memberId, labels),
  };
}

function relevantOperation(operation, editor) {
  const key = operation?.entity_key || {};
  return (
    operation?.table_name === editor.memberTable &&
    text(key[editor.memberGroupField]) === editor.groupId
  );
}

export function effectiveMembers(detail, operations, labels = {}) {
  const editor = config(detail);
  const rows = new Map();
  for (const [index, row] of (detail?.members || []).entries()) {
    const record = memberRecord(row, editor, labels, (index + 1) * 10);
    rows.set(record.member_id, record);
  }
  for (const operation of Array.isArray(operations) ? operations : []) {
    if (!relevantOperation(operation, editor)) continue;
    const key = operation.entity_key || {};
    const memberId = text(key[editor.memberIdField]);
    if (!memberId) continue;
    if (operation.action === "delete") {
      rows.delete(memberId);
      continue;
    }
    const prior = rows.get(memberId) || {};
    rows.set(
      memberId,
      memberRecord({ ...prior, ...(operation.final || {}), [editor.memberIdField]: memberId },
        editor, labels, (rows.size + 1) * 10),
    );
  }
  return [...rows.values()].sort((left, right) =>
    left.display_order - right.display_order || left.member_id.localeCompare(right.member_id)
  );
}

function normalizedOrders(members) {
  const values = members.map((member) => member.display_order);
  if (values.every(Number.isFinite) && new Set(values).size === values.length) {
    return members.map((member) => ({ ...member }));
  }
  return members.map((member, index) => ({ ...member, display_order: (index + 1) * 10 }));
}

export function moveMember(members, memberId, direction) {
  const ordered = normalizedOrders(members);
  const current = ordered.findIndex((member) => member.member_id === memberId);
  const target = current + Math.sign(direction);
  if (current < 0 || target < 0 || target >= ordered.length || direction === 0) return ordered;
  const currentOrder = ordered[current].display_order;
  ordered[current].display_order = ordered[target].display_order;
  ordered[target].display_order = currentOrder;
  return ordered.sort((left, right) =>
    left.display_order - right.display_order || left.member_id.localeCompare(right.member_id)
  );
}

export function addMember(members, detail, memberId, label) {
  const editor = config(detail);
  const value = text(memberId).trim();
  if (!value || members.some((member) => member.member_id === value)) return members;
  const maxOrder = members.reduce(
    (maximum, member) => Math.max(maximum, numberOrder(member.display_order, 0)), 0,
  );
  return [...members, {
    [editor.memberGroupField]: editor.groupId,
    [editor.memberIdField]: value,
    member_id: value,
    [editor.memberOrderField]: maxOrder + 10,
    display_order: maxOrder + 10,
    [editor.memberActiveField]: "True",
    active: "True",
    label: text(label).trim() || value,
  }];
}

export function removeMember(members, memberId) {
  return members.filter((member) => member.member_id !== memberId);
}

export function groupDependencyCounts(dependents, detail, members) {
  const editor = config(detail);
  const counts = new Map();
  if (members.length) counts.set(editor.memberTable, members.length);
  for (const dependency of Array.isArray(dependents) ? dependents : []) {
    const table = text(dependency?.table) || "connected record";
    if (table === editor.memberTable) continue;
    counts.set(table, (counts.get(table) || 0) + 1);
  }
  return [...counts.entries()].map(([table, count]) => ({ table, count }));
}

export function membershipOperations(originalMembers, desiredMembers, detail) {
  const editor = config(detail);
  const original = new Map(originalMembers.map((member) => [member.member_id, member]));
  const desired = new Map(desiredMembers.map((member) => [member.member_id, member]));
  const operations = [];
  for (const member of originalMembers) {
    if (!desired.has(member.member_id)) {
      operations.push({
        table: editor.memberTable,
        model_id: editor.modelId,
        op: "delete",
        key: {
          [editor.memberGroupField]: editor.groupId,
          [editor.memberIdField]: member.member_id,
        },
        record: null,
      });
    }
  }
  for (const member of desiredMembers) {
    const before = original.get(member.member_id);
    const desiredOrder = member.display_order ?? member[editor.memberOrderField];
    const desiredActive = member.active ?? member[editor.memberActiveField];
    const record = {
      [editor.memberGroupField]: editor.groupId,
      [editor.memberIdField]: member.member_id,
      [editor.memberOrderField]: desiredOrder,
      [editor.memberActiveField]: desiredActive,
    };
    if (!before) {
      operations.push({
        table: editor.memberTable,
        model_id: editor.modelId,
        op: "add",
        key: {
          [editor.memberGroupField]: editor.groupId,
          [editor.memberIdField]: member.member_id,
        },
        record,
      });
    } else if (
      numberOrder(before.display_order, 0) !== numberOrder(desiredOrder, 0) ||
      text(before.active) !== text(desiredActive)
    ) {
      operations.push({
        table: editor.memberTable,
        model_id: editor.modelId,
        op: "update",
        key: {
          [editor.memberGroupField]: editor.groupId,
          [editor.memberIdField]: member.member_id,
        },
        record,
      });
    }
  }
  return operations;
}
