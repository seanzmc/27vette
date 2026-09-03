import React, { useEffect, useMemo, useState } from "react";
import { Filter, LayoutPanelTop, Pencil, X } from "lucide-react";
import { api } from "../api.js";
import { hasDraftOverlay, overlayBlockReason, overlayStateLabel, sectionHeadingField } from "../draftOverlayModel.js";
import DraftOverlay, { EffectiveText } from "./DraftOverlay.jsx";
import RecordForm from "./RecordForm.jsx";

const FILTERS = [
  ["all", "All sections"],
  ["unresolved", "Unresolved"],
  ["empty", "Empty sections"],
  ["inactive", "Inactive"],
  ["buckets", "Buckets"],
  ["draft", "Draft changes"],
];

const EDIT_FAMILY_LABELS = {
  context_sections: "context_section_master",
  section_presentation: "section_presentation",
};

const SECTION_FIELD_GROUPS = [
  { label: "Section identity", fields: ["section_id", "display_label", "section_name"] },
  {
    label: "Form placement and display",
    fields: [
      "step_key", "section_display_order", "display_behavior",
      "standard_equipment_bucket", "standard_equipment_group_type",
      "auto_added_bucket", "active",
    ],
  },
  {
    label: "Selection behavior",
    fields: [
      "context_type", "selection_mode", "choice_mode", "is_required",
      "standard_behavior", "step_label",
    ],
  },
  { label: "Operator notes", fields: ["notes"] },
];

function matchesFilter(section, filter) {
  if (filter === "unresolved") return section.classification === "unresolved";
  if (filter === "empty") return section.empty;
  if (filter === "inactive") return section.classification === "inactive";
  if (filter === "buckets") return section.classification === "bucket_section";
  if (filter === "draft") return hasDraftOverlay(section.draft_overlay);
  return true;
}

function stateLabel(section) {
  if (hasDraftOverlay(section.draft_overlay)) {
    return overlayStateLabel(section.draft_overlay);
  }
  if (section.classification === "bucket_section") return "Bucket";
  if (section.classification === "unresolved") return "Unresolved";
  if (section.classification === "inactive") return "Inactive";
  if (section.display_behavior) return section.display_behavior.replaceAll("_", " ");
  return "Active";
}

export default function SectionsLayout({
  modelKey,
  navigation,
  onNavigationChange,
  draftId,
  draftRevision,
  draftMutable,
  onChanged,
}) {
  const [structure, setStructure] = useState(null);
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setStructure(await api.structure(modelKey, draftId));
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  };

  useEffect(() => {
    setStructure(null);
    setEditing(null);
    load();
  }, [modelKey, draftId, draftRevision]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedId = navigation.type === "section" ? navigation.id : "";
  const selected = structure?.graph.section_nodes.find(
    (section) => section.section_id === selectedId
  ) || null;
  // A conflicted graph overlay (stale binding, terminal draft) blocks every
  // section mutation with the exact reason; authored values stay displayed.
  const graphOverlay = structure?.graph.draft_overlay;
  const graphBlocked = graphOverlay?.state === "conflicted"
    ? overlayBlockReason(graphOverlay) : "";
  const editBlocked = !draftMutable
    ? "The active draft is locked; start a new draft to edit." : graphBlocked;
  const visible = useMemo(
    () => (structure?.graph.section_nodes || []).filter(
      (section) => matchesFilter(section, filter)
    ),
    [structure, filter],
  );

  const navigateSection = (sectionId) => onNavigationChange({
    ...navigation,
    workspace: "sections",
    type: sectionId ? "section" : "",
    id: sectionId,
  });

  const navigateOption = (option) => onNavigationChange({
    ...navigation,
    workspace: option.destination.workspace,
    type: option.destination.entity_type,
    id: option.destination.entity_id,
  });

  const startEdit = async (section) => {
    let table = section.editor?.table;
    let mode = "edit";
    let initial = section.editor?.record;
    if (!table) {
      table = "section_presentation";
      mode = "add";
      initial = {
        model_key: modelKey,
        section_id: section.section_id,
        step_key: section.step_key,
        section_display_order: section.section_display_order,
        active: "True",
      };
    }
    try {
      const schema = await api.schema(table, modelKey);
      setEditing({
        table,
        mode,
        initial,
        schema,
        title: `${mode === "add" ? "Add display metadata" : "Edit section"} · ${section.display_name}`,
        target: `${section.display_name} · ${EDIT_FAMILY_LABELS[table]}`,
      });
      setError("");
    } catch (schemaError) {
      setError(`Editor controls are unavailable: ${schemaError.message}`);
    }
  };

  const saveDraft = (payload) => api.saveDraftOperation(draftId, {
    ...payload,
    actor: "workbook-manager-ui",
    session_id: "browser",
  });

  const saved = async () => {
    setEditing(null);
    await onChanged();
    await load();
  };

  return (
    <section className="sections-workspace">
      <div className="workspace-hero sections-hero">
        <div>
          <span className="eyebrow">Connected form graph</span>
          <h2><LayoutPanelTop size={21} /> Sections &amp; Layout</h2>
          <p>
            Runtime sequence, customer sections, buckets, context, summaries, placed options,
            draft changes, and fresh-runtime parity for the selected model.
          </p>
        </div>
        {structure && (
          <div className="graph-counts" aria-label="Form graph counts">
            <strong>{structure.graph.counts.sections}</strong><span>sections</span>
            <strong>{structure.graph.counts.buckets}</strong><span>buckets</span>
            <strong>{structure.graph.counts.unresolved}</strong><span>unresolved</span>
            <strong>{structure.graph.counts.draft_changes}</strong><span>draft changes</span>
          </div>
        )}
      </div>

      {error && <div className="notice err" role="alert">{error}</div>}
      {!structure && !error && <div className="panel empty">Loading connected form graph…</div>}

      {structure && (
        <>
          <section className="panel runtime-sequence" aria-label="Runtime sequence">
            <div className="panel-head">
              <strong>Runtime sequence</strong>
              <span className="muted">Order is workbook-authored in runtime_steps_meta.</span>
            </div>
            <ol>
              {structure.graph.steps.map((step) => (
                <li key={step.step_key}>
                  <span>{step.runtime_order}</span>
                  <strong>{step.display_name}</strong>
                  <small>{step.section_count} section{step.section_count === 1 ? "" : "s"}</small>
                  {hasDraftOverlay(step.draft_overlay) && <em>{overlayStateLabel(step.draft_overlay)}</em>}
                </li>
              ))}
            </ol>
          </section>

          <div className="section-filter-bar" aria-label="Filter sections">
            <Filter size={15} />
            {FILTERS.map(([key, label]) => (
              <button
                type="button"
                key={key}
                className={`btn small ${filter === key ? "primary" : ""}`}
                aria-pressed={filter === key}
                onClick={() => setFilter(key)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className={`sections-layout ${selected ? "has-detail" : ""}`}>
            <div className="section-node-list panel">
              {!visible.length && <div className="empty">No sections match this filter.</div>}
              {visible.map((section) => (
                <button
                  type="button"
                  key={section.section_id}
                  className={`section-node ${selectedId === section.section_id ? "selected" : ""}`}
                  onClick={() => navigateSection(section.section_id)}
                >
                  <span>
                    <strong>{section.display_name}</strong>
                    <small className="mono">{section.section_id}</small>
                  </span>
                  <span>
                    <small>{section.step_key || "No step"}</small>
                    <span className="chip">{stateLabel(section)}</span>
                  </span>
                  <span>{section.options.length} options · {section.variant_overrides.length} overrides</span>
                </button>
              ))}
            </div>

            {selected && (
              <aside className="section-detail panel" aria-label="Connected section detail">
                <div className="section-detail-heading">
                  <div>
                    <span className="eyebrow">Connected section detail</span>
                    <h2><EffectiveText overlay={selected.draft_overlay} field={sectionHeadingField(selected.draft_overlay)} authored={selected.authored_display_name ?? selected.display_name} /></h2>
                    <span className="mono faint">{selected.section_id}</span>
                  </div>
                  <button className="icon-btn" type="button" onClick={() => navigateSection("")} aria-label="Close section detail">
                    <X size={17} />
                  </button>
                </div>

                <div className="detail-facts">
                  <div><span>Runtime placement</span><strong><EffectiveText overlay={selected.draft_overlay} field="step_key" authored={selected.step_key || "Unresolved"} /></strong></div>
                  <div><span>Workbook evidence</span><strong>{selected.workbook_evidence}</strong></div>
                  <div><span>Fresh-runtime evidence</span><strong>{selected.runtime_evidence}</strong></div>
                  <div><span>State</span><strong>{stateLabel(selected)}</strong></div>
                </div>

                <div className="parity-impact">
                  <strong>Parity impact</strong>
                  <span>{structure.graph.parity.draft_impact || "No draft graph changes."}</span>
                  <small>Base: {structure.graph.parity.base_status.replaceAll("_", " ")}</small>
                </div>

                {graphBlocked && (
                  <div className="notice err" role="alert">{graphBlocked} Authored values remain in effect.</div>
                )}
                <DraftOverlay overlay={selected.draft_overlay} impactLabels={{ options: "Options" }} testId="section-draft-overlay" />

                <div className="section-detail-actions">
                  {selected.editor ? (
                    <button className="btn primary" disabled={Boolean(editBlocked)} title={editBlocked || "Edit section"} onClick={() => startEdit(selected)}>
                      <Pencil size={14} /> Edit section
                    </button>
                  ) : (
                    <>
                      <span className="readonly-label">Reference only · section_master</span>
                      <button className="btn" disabled={Boolean(editBlocked)} title={editBlocked || "Add display metadata"} onClick={() => startEdit(selected)}>
                        Add display metadata
                      </button>
                    </>
                  )}
                </div>

                <section className="detail-options">
                  <h3>Options in this section</h3>
                  {!selected.options.length && <p className="muted">No option rows use this section.</p>}
                  {selected.options.map((option) => (
                    <button key={option.option_id} type="button" onClick={() => navigateOption(option)}>
                      <span><strong>{option.rpo || option.option_id}</strong> {option.option_name}</span>
                      <span>{option.active === "True" ? "Active" : "Inactive"}</span>
                    </button>
                  ))}
                </section>

                {!!selected.variant_overrides.length && (
                  <section className="detail-overrides">
                    <h3>Variant placement overrides</h3>
                    {selected.variant_overrides.map((override, index) => (
                      <div key={`${override.option_id}-${override.variant_id}-${index}`}>
                        <strong>{override.option_id}</strong>
                        <span>{override.variant_name || override.variant_id}</span>
                      </div>
                    ))}
                  </section>
                )}
              </aside>
            )}
          </div>

          <details className="panel summary-mappings">
            <summary>Context and summary mappings</summary>
            <div className="summary-map-grid">
              {structure.graph.summary_only.map((summary) => (
                <div className="summary-map-card" key={summary.section_key}>
                  <strong>{summary.section_label}</strong>
                  <span>{summary.step_keys.join(", ") || "No contributing step"}</span>
                </div>
              ))}
            </div>
          </details>
        </>
      )}

      {editing && (
        <RecordForm
          key={`${editing.table}-${editing.mode}-${editing.initial?.id ?? editing.initial?.section_id ?? "new"}`}
          schema={editing.schema}
          mode={editing.mode}
          initial={editing.initial}
          modelKey={modelKey}
          fieldGroups={SECTION_FIELD_GROUPS}
          saveFn={saveDraft}
          onSaved={saved}
          onCancel={() => setEditing(null)}
          saveLabel="Save section change to draft"
          title={editing.title}
          target={editing.target}
        />
      )}
    </section>
  );
}
