import React, { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Check, ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import { api } from "../api.js";
import {
  addMember,
  applyGroupDraftOverlay,
  effectiveMembers,
  initialGroupDraft,
  matchingGroupOperation,
  membershipOperations,
  moveMember,
  removeMember,
} from "../groupEditorModel.js";
import EditorShell from "./EditorShell.jsx";
import RecordForm from "./RecordForm.jsx";

const GROUP_FIELD_GROUPS = [
  { label: "Identity and heading", fields: ["group_id", "display_label"] },
  {
    label: "Behavior and availability",
    fields: [
      "group_type", "selection_mode", "source_id", "body_style_scope",
      "trim_level_scope", "variant_scope", "disabled_reason", "active",
    ],
  },
  { label: "Operator notes", fields: ["notes"] },
];

function FieldDiff({ operation }) {
  const changed = Object.entries(operation?.changed_fields || {});
  return (
    <div className="group-editor-overlay" data-testid="group-draft-overlay">
      <h3>Draft overlay</h3>
      {!changed.length ? (
        <p className="muted">No effective draft changes remain for this group.</p>
      ) : (
        <div className="field-diff">
          {changed.map(([field, pair]) => (
            <React.Fragment key={field}>
              <div className="field-name">{field}</div>
              <div className="before-value">
                {pair.before === null ? <em>SQL NULL</em> : String(pair.before)}
              </div>
              <div className="after-value">
                {pair.after === null ? <em>SQL NULL</em> : String(pair.after)}
              </div>
            </React.Fragment>
          ))}
        </div>
      )}
      <p className="muted">
        Saved to the durable draft only. The workbook changes only through Apply
        and Rebuild.
      </p>
    </div>
  );
}

function GroupFactsEditor({
  detail, modelKey, draftId, draftMutable, schema, operations, onClose, onChanged,
}) {
  const [savedOperation, setSavedOperation] = useState(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const projected = useMemo(
    () => initialGroupDraft(detail, schema),
    [detail, schema],
  );
  const initial = useMemo(
    () => applyGroupDraftOverlay(
      projected.draft,
      hasSubmitted ? savedOperation : matchingGroupOperation(operations, detail),
    ),
    [projected, operations, detail, savedOperation, hasSubmitted],
  );

  const saveGroup = async (payload) => {
    if (!draftMutable || !draftId) {
      throw new Error("The active draft is locked; start a new draft to edit.");
    }
    return api.saveDraftOperation(draftId, {
      ...payload,
      actor: "workbook-manager-ui",
      session_id: "browser",
    });
  };

  if (showOverlay) return (
    <EditorShell
      title={`Edit group · ${detail.label}`}
      subtitle="The connected group stays open behind this durable draft overlay."
      target={`${detail.label} · ${detail.group.src_sheet || projected.target.table}`}
      dirty={false}
      busy={false}
      onRequestClose={onClose}
      footer={(requestClose) => (
        <>
          <button type="button" className="btn small" onClick={() => setShowOverlay(false)}>
            <ArrowLeft size={14} /> Keep editing
          </button>
          <button type="button" className="btn primary small" onClick={requestClose}>Close</button>
        </>
      )}
    >
      <FieldDiff operation={savedOperation} />
    </EditorShell>
  );

  return (
    <RecordForm
      key={`${detail.group_id}:${savedOperation?.id || "projected"}`}
      schema={schema}
      mode="edit"
      initial={initial}
      modelKey={modelKey}
      fieldGroups={GROUP_FIELD_GROUPS}
      saveFn={saveGroup}
      onSaved={(operation) => {
        setSavedOperation(operation);
        setHasSubmitted(true);
        setShowOverlay(true);
        Promise.resolve(onChanged?.()).catch(() => {});
      }}
      onCancel={onClose}
      saveLabel="Save group change to draft"
      title={`Edit group · ${detail.label}`}
      target={`${detail.label} · ${detail.group.src_sheet || projected.target.table}`}
    />
  );
}

function dependencySummary(dependencies) {
  if (!dependencies?.length) return "";
  const counts = new Map();
  for (const dependency of dependencies) {
    const label = dependency.table || "connected record";
    counts.set(label, (counts.get(label) || 0) + 1);
  }
  return [...counts.entries()].map(([label, count]) => `${count} ${label}`).join(", ");
}

function MemberEditor({
  detail, draftId, draftMutable, memberSchema, operations, onClose, onChanged,
}) {
  const [referenceOptions, setReferenceOptions] = useState([]);
  const [referenceQuery, setReferenceQuery] = useState("");
  const [selectedMember, setSelectedMember] = useState("");
  const [loadingReferences, setLoadingReferences] = useState(false);
  const [original, setOriginal] = useState([]);
  const [desired, setDesired] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const loaded = useRef(false);
  const memberIdField = detail.editor.member_id_field;

  const loadReferences = async (query = "") => {
    setLoadingReferences(true);
    setError("");
    try {
      const response = await api.referenceOptions(
        detail.editor.member_table,
        memberIdField,
        { model: detail.model_key, query, limit: 100 },
      );
      setReferenceOptions(response.options || []);
    } catch (loadError) {
      setError(`Member choices are unavailable: ${loadError.message}`);
    } finally {
      setLoadingReferences(false);
    }
  };

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    const labels = Object.fromEntries(
      referenceOptions.map((option) => [String(option.value), option.label]),
    );
    const members = effectiveMembers(detail, operations, labels);
    setOriginal(members);
    setDesired(members);
    loadReferences();
  }, [detail, operations]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!referenceOptions.length) return;
    const labels = Object.fromEntries(
      referenceOptions.map((option) => [String(option.value), option.label]),
    );
    setOriginal((current) => current.map((member) => ({
      ...member, label: labels[member.member_id] || member.label,
    })));
    setDesired((current) => current.map((member) => ({
      ...member, label: labels[member.member_id] || member.label,
    })));
  }, [referenceOptions]);

  const plan = useMemo(
    () => membershipOperations(original, desired, detail),
    [original, desired, detail],
  );

  const addSelected = () => {
    const option = referenceOptions.find(
      (candidate) => String(candidate.value) === selectedMember,
    );
    setDesired((current) => addMember(current, detail, selectedMember, option?.label));
    setSelectedMember("");
    setNotice("");
  };

  const saveMembership = async () => {
    if (!draftMutable || !draftId) {
      setError("The active draft is locked; start a new draft to edit.");
      return;
    }
    if (!plan.length) {
      setNotice("No effective membership changes remain to save.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      for (const operation of plan) {
        await api.saveDraftOperation(draftId, {
          ...operation,
          actor: "workbook-manager-ui",
          session_id: "browser",
        });
      }
      setOriginal(desired.map((member) => ({ ...member })));
      setNotice(`${plan.length} membership operation${plan.length === 1 ? "" : "s"} saved to the durable draft.`);
      await onChanged?.();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setBusy(false);
    }
  };

  const requestGroupRemoval = async () => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api.dependencies(
        detail.editor.group_table,
        detail.model_key,
        { group_id: detail.group_id },
      );
      if (result.count) {
        setError(
          `Group removal refused: ${dependencySummary(result.dependents)} still depend on this group. ` +
          "Remove the dependent members first; the complete final graph is checked again in Review & Apply.",
        );
        return;
      }
      if (!window.confirm(`Remove ${detail.label} from the durable draft?`)) return;
      await api.saveDraftOperation(draftId, {
        table: detail.editor.group_table,
        model_id: detail.model_key,
        op: "delete",
        key: { group_id: detail.group_id },
        record: null,
        actor: "workbook-manager-ui",
        session_id: "browser",
      });
      setNotice("Group removal saved to the durable draft. Final-graph preview remains authoritative.");
      await onChanged?.();
    } catch (removeError) {
      setError(removeError.message);
    } finally {
      setBusy(false);
    }
  };

  const availableOptions = referenceOptions.filter(
    (option) => !desired.some((member) => member.member_id === String(option.value)),
  );
  const referenceColumn = memberSchema.columns.find((column) => column.name === memberIdField);

  return (
    <EditorShell
      title={`Manage members · ${detail.label}`}
      subtitle="Add, remove, activate, or reorder existing members in the durable draft."
      target={`${detail.label} · ${detail.editor.member_table}`}
      dirty={plan.length > 0}
      busy={busy}
      onRequestClose={onClose}
      footer={(requestClose) => (
        <>
          <button type="button" className="btn primary" onClick={saveMembership} disabled={busy}>
            <Check size={15} /> {busy ? "Saving to draft…" : "Save membership changes to draft"}
          </button>
          <button type="button" className="btn" onClick={requestClose} disabled={busy}>Cancel</button>
          <span className="muted">Draft only · no workbook write or rebuild</span>
        </>
      )}
    >
      <section className="member-add-panel" aria-labelledby="member-add-heading">
        <h3 id="member-add-heading">Add existing member</h3>
        <div className="member-reference-search">
          <label>
            <span>{referenceColumn?.control?.label || "Option or target"}</span>
            <input
              className="text"
              value={referenceQuery}
              onChange={(event) => setReferenceQuery(event.target.value)}
              onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }}
              placeholder="Search by RPO, name, or canonical ID"
            />
          </label>
          <button type="button" className="btn small" onClick={() => loadReferences(referenceQuery)} disabled={loadingReferences}>
            {loadingReferences ? "Searching…" : "Search choices"}
          </button>
        </div>
        <div className="member-add-row">
          <select value={selectedMember} onChange={(event) => setSelectedMember(event.target.value)} disabled={loadingReferences}>
            <option value="">Choose an existing member</option>
            {availableOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <button type="button" className="btn small" onClick={addSelected} disabled={!selectedMember}>
            <Plus size={14} /> Add existing member
          </button>
        </div>
      </section>

      <section aria-labelledby="final-member-order-heading">
        <h3 id="final-member-order-heading">Proposed final order</h3>
        <p className="muted">
          Orders are unique and deterministic. Moving one member swaps only the
          adjacent values unless the existing order requires normalization.
        </p>
        <ol className="member-order-list">
          {desired.map((member, index) => (
            <li key={member.member_id} className={member.active === "True" ? "" : "inactive"}>
              <span className="member-order-number">{member.display_order}</span>
              <span className="member-order-label">
                <strong>{member.label}</strong>
                <small>{member.active === "True" ? "Active member" : "Inactive member"}</small>
              </span>
              <label className="member-active-toggle">
                <input
                  type="checkbox"
                  checked={member.active === "True"}
                  onChange={(event) => setDesired((current) => current.map((row) =>
                    row.member_id === member.member_id
                      ? { ...row, active: event.target.checked ? "True" : "False" }
                      : row
                  ))}
                /> Active
              </label>
              <span className="member-order-actions">
                <button
                  type="button" className="btn icon" aria-label={`Move up ${member.label}`}
                  title="Move up" disabled={index === 0 || busy}
                  onClick={() => setDesired((current) => moveMember(current, member.member_id, -1))}
                ><ChevronUp size={15} /><span className="sr-only">Move up</span></button>
                <button
                  type="button" className="btn icon" aria-label={`Move down ${member.label}`}
                  title="Move down" disabled={index === desired.length - 1 || busy}
                  onClick={() => setDesired((current) => moveMember(current, member.member_id, 1))}
                ><ChevronDown size={15} /><span className="sr-only">Move down</span></button>
                <button
                  type="button" className="btn icon danger" aria-label={`Remove ${member.label}`}
                  title="Remove member" disabled={busy}
                  onClick={() => setDesired((current) => removeMember(current, member.member_id))}
                ><Trash2 size={15} /><span className="sr-only">Remove member</span></button>
              </span>
            </li>
          ))}
        </ol>
        {!desired.length && <div className="notice warn">This proposal leaves the group with no members. Final-graph preview may refuse it.</div>}
      </section>

      {notice && <div className="notice ok" role="status">{notice}</div>}
      {error && <div className="notice err" role="alert">{error}</div>}
      <div className="group-danger-zone">
        <h3>Remove group</h3>
        <p>Direct dependents are inspected first. A group with remaining members is refused here.</p>
        <button type="button" className="btn danger small" onClick={requestGroupRemoval} disabled={busy || !draftMutable}>
          <Trash2 size={14} /> Remove group from draft
        </button>
      </div>
    </EditorShell>
  );
}

export default function GroupEditor({
  detail, mode, modelKey, draftId, draftMutable, onClose, onChanged,
}) {
  const [groupSchema, setGroupSchema] = useState(null);
  const [memberSchema, setMemberSchema] = useState(null);
  const [operations, setOperations] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let current = true;
    Promise.all([
      api.schema(detail.editor.group_table, modelKey),
      api.schema(detail.editor.member_table, modelKey),
      draftId ? api.draftOperations(draftId) : Promise.resolve({ operations: [] }),
    ]).then(([group, member, draft]) => {
      if (!current) return;
      setGroupSchema(group);
      setMemberSchema(member);
      setOperations(draft.operations || []);
    }).catch((loadError) => {
      if (current) setError(loadError.message);
    });
    return () => { current = false; };
  }, [detail, modelKey, draftId]);

  if (!groupSchema || !memberSchema || operations === null) return (
    <EditorShell
      title={`${mode === "members" ? "Manage members" : "Edit group"} · ${detail.label}`}
      subtitle="Loading registry controls and durable draft evidence."
      target={detail.label}
      dirty={false}
      busy={false}
      onRequestClose={onClose}
    >
      {error ? <div className="notice err" role="alert">{error}</div> : <p>Loading editor…</p>}
    </EditorShell>
  );

  if (mode === "members") return (
    <MemberEditor
      detail={detail}
      draftId={draftId}
      draftMutable={draftMutable}
      memberSchema={memberSchema}
      operations={operations}
      onClose={onClose}
      onChanged={onChanged}
    />
  );

  return (
    <GroupFactsEditor
      detail={detail}
      modelKey={modelKey}
      draftId={draftId}
      draftMutable={draftMutable}
      schema={groupSchema}
      operations={operations}
      onClose={onClose}
      onChanged={onChanged}
    />
  );
}
