import React, { useEffect, useState } from "react";
import {
  BookOpen, Boxes, ChevronRight, Layers, LockKeyhole, Pencil, TriangleAlert,
} from "lucide-react";
import { api } from "../api.js";
import { humanize } from "../naming.js";
import RecordForm from "./RecordForm.jsx";

const STEP_FIELD_GROUPS = [
  { label: "Customer step", fields: ["step_key", "step_label"] },
  { label: "Runtime placement", fields: ["runtime_order", "source", "active"] },
  { label: "Operator notes", fields: ["notes"] },
];

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

function SectionCard({ section, draftMutable, onEdit }) {
  const editable = Boolean(section.editor);
  return (
    <article className="form-section-card">
      <div className="form-section-card-copy">
        <strong>{section.display_name}</strong>
        <span className="mono faint">{section.section_id}</span>
        <span className="section-evidence">
          Workbook: {section.workbook_evidence} · Fresh runtime: {section.runtime_evidence}
        </span>
        <div className="tags">
          <span className="chip">{section.option_count} options</span>
          {section.interior_count > 0 && (
            <span className="chip">{section.interior_count} interiors</span>
          )}
          {section.display_behavior && (
            <span className="chip warn">{section.display_behavior.replaceAll("_", " ")}</span>
          )}
        </div>
      </div>
      {editable ? (
        <button
          type="button"
          className="btn small"
          disabled={!draftMutable}
          onClick={() => onEdit(section)}
        >
          <Pencil size={14} /> Edit section
        </button>
      ) : (
        <div className="section-reference-actions">
          <span className="readonly-label">
            <LockKeyhole size={13} /> Reference only
          </span>
          <span className="muted">{section.read_only_reason}</span>
          <button
            type="button"
            className="btn small"
            disabled={!draftMutable}
            onClick={() => onEdit(section)}
          >
            Add display metadata
          </button>
        </div>
      )}
    </article>
  );
}

export default function FormStructure({
  models, modelKey, setModelKey, draftId, draftMutable, onChanged,
}) {
  const [structure, setStructure] = useState(null);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = async (key) => {
    try {
      setStructure(await api.structure(key));
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  };

  useEffect(() => {
    setStructure(null);
    setEditing(null);
    if (modelKey) load(modelKey);
  }, [modelKey]);

  const startEdit = async ({
    table, mode = "edit", initial, title, target, saveLabel, fieldGroups,
  }) => {
    try {
      const schema = await api.schema(table, modelKey);
      setEditing({
        table, mode, initial: initial || {}, schema, title, target, saveLabel, fieldGroups,
      });
      setError("");
    } catch (schemaError) {
      setError(`Editor controls are unavailable: ${schemaError.message}`);
    }
  };

  const editStep = (step) => startEdit({
    table: "form_steps",
    initial: step,
    title: `Edit step · ${step.display_name}`,
    target: `${step.display_name} · runtime_steps`,
    saveLabel: "Save step change to draft",
    fieldGroups: STEP_FIELD_GROUPS,
  });

  const editSection = (section) => {
    if (section.origins.includes("context_sections")) {
      const record = structure.context_sections.find(
        (row) => row.section_id === section.section_id
      );
      return startEdit({
        table: "context_sections",
        initial: record,
        title: `Edit section · ${section.display_name}`,
        target: `${section.display_name} · context_section_master`,
        saveLabel: "Save section change to draft",
        fieldGroups: SECTION_FIELD_GROUPS,
      });
    }
    if (section.editor) {
      return startEdit({
        table: "section_presentation",
        initial: section.editor.record,
        title: `Edit section · ${section.display_name}`,
        target: `${section.display_name} · section_presentation`,
        saveLabel: "Save section change to draft",
        fieldGroups: SECTION_FIELD_GROUPS,
      });
    }
    return startEdit({
      table: "section_presentation",
      mode: "add",
      initial: {
        model_key: modelKey,
        section_id: section.section_id,
        step_key: section.step_key,
        section_display_order: section.section_display_order,
        active: "True",
      },
      title: `Add display metadata · ${section.display_name}`,
      target: `${section.display_name} · section_presentation`,
      saveLabel: "Save section change to draft",
      fieldGroups: SECTION_FIELD_GROUPS,
    });
  };

  const saved = async () => {
    setEditing(null);
    await load(modelKey);
    onChanged();
  };

  const saveDraft = (payload) => api.saveDraftOperation(draftId, {
    ...payload,
    actor: "workbook-manager-ui",
    session_id: "browser",
  });

  const model = models.find((item) => item.model_key === modelKey);

  return (
    <div>
      <div className="section-heading"><Layers size={14} /> Model activation sequence</div>
      <div className="model-grid">
        {models.map((item) => (
          <button
            key={item.model_key}
            className={`model-card ${item.model_key === modelKey ? "selected" : ""} ${item.scaffold ? "scaffold" : ""}`}
            onClick={() => setModelKey(item.model_key)}
          >
            <div className="name">
              {item.label}<span className="faint mono">{item.model_year}</span>
            </div>
            <div className="tags">
              <span className={`chip ${item.active === "True" ? "on" : "off"}`}>
                {item.active === "True" ? "Active" : "Scaffold"}
              </span>
              {item.promoted_to_runtime === "True" && <span className="chip blue">Runtime</span>}
              {item.default_model === "True" && <span className="chip warn">Default</span>}
            </div>
          </button>
        ))}
      </div>

      <div className="toolbar form-overview-toolbar">
        <button
          type="button"
          className="btn small"
          disabled={!draftMutable || !model}
          onClick={() => model && startEdit({
            table: "models",
            initial: model,
            title: `Edit model · ${model.label}`,
            target: `${model.label} · model_master`,
            saveLabel: "Save model change to draft",
          })}
        >
          <Pencil size={14} /> Edit model metadata &amp; Vehicle Setup copy
        </button>
        {!draftMutable && (
          <span className="muted">Editing blocked: this draft is locked. Start a new draft to edit.</span>
        )}
      </div>

      {error && <div className="notice err" role="alert">{error}</div>}
      {!structure && !error && <div className="panel empty">Loading form graph…</div>}

      {structure && (
        <>
          <div className="section-heading">
            <ChevronRight size={14} /> Runtime steps &amp; interface sections — {humanize(modelKey)}
          </div>
          <div className="panel form-graph" data-graph-version={structure.graph.version}>
            {!structure.graph.steps.length && (
              <div className="empty">No active workbook-owned runtime steps for this model.</div>
            )}
            {structure.graph.steps.map((step, index) => (
              <section className="step-row" key={step.step_key}>
                <span className="step-num">{step.runtime_order || index + 1}</span>
                <div className="step-main">
                  <div className="step-title-row">
                    <div>
                      <div className="label">{step.display_name}</div>
                      <div className="key">{step.step_key}</div>
                    </div>
                    <button
                      type="button"
                      className="btn small"
                      disabled={!draftMutable}
                      onClick={() => editStep(step)}
                    >
                      <Pencil size={14} /> Edit step
                    </button>
                  </div>
                  <div className="step-sections">
                    {!step.sections.length ? (
                      <div className="proven-empty">
                        <BookOpen size={14} />
                        <span><strong>No section cards</strong> — {step.empty_reason}</span>
                      </div>
                    ) : step.sections.map((section) => (
                      <SectionCard
                        key={section.section_id}
                        section={section}
                        draftMutable={draftMutable}
                        onEdit={editSection}
                      />
                    ))}
                  </div>
                </div>
              </section>
            ))}
          </div>

          <div className="section-heading"><Boxes size={14} /> Standard equipment buckets</div>
          <div className="panel graph-classification-panel">
            <p className="muted">
              These are customer-data buckets, not navigable form steps. They are shown separately so they are never reported as broken steps.
            </p>
            {structure.graph.buckets.map((bucket) => (
              <section key={bucket.step_key} className="bucket-group">
                <h3>{bucket.label} <span className="chip">{bucket.member_count} sections</span></h3>
                <div className="section-card-grid">
                  {bucket.members.map((section) => (
                    <SectionCard
                      key={section.section_id}
                      section={section}
                      draftMutable={draftMutable}
                      onEdit={editSection}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="section-heading">Summary-only review sections</div>
          <div className="panel graph-classification-panel">
            <p className="muted">
              Review-summary headings and their contributing runtime steps. These mappings do not create navigable form sections.
            </p>
            <div className="summary-map-grid">
              {structure.graph.summary_only.map((summary) => (
                <div className="summary-map-card" key={summary.section_key}>
                  <strong>{summary.section_label}</strong>
                  <span className="mono faint">{summary.section_key}</span>
                  <span>{summary.step_keys.length ? summary.step_keys.join(", ") : "No contributing runtime step"}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="section-heading"><TriangleAlert size={14} /> Unmapped authoring records</div>
          <div className="panel graph-classification-panel">
            {!structure.graph.unmapped_sections.length ? (
              <div className="empty">No model-connected section has an unresolved or invalid step relationship.</div>
            ) : (
              structure.graph.unmapped_sections.map((section) => (
                <div className="unmapped-row" key={section.section_id}>
                  <strong>{section.display_name}</strong>
                  <span>{section.reason}</span>
                  <button className="btn small" disabled={!draftMutable} onClick={() => editSection(section)}>
                    Review section metadata
                  </button>
                </div>
              ))
            )}
          </div>

          <details className="panel inactive-structure">
            <summary>Inactive structure records</summary>
            <p className="muted">
              {structure.graph.inactive_records.steps.length} steps · {structure.graph.inactive_records.context_sections.length} context sections · {structure.graph.inactive_records.section_presentation.length} presentation rows
            </p>
          </details>

          <details className="panel variant-reference">
            <summary>Variant reference</summary>
            <table className="data">
              <thead>
                <tr>
                  <th>Variant</th><th>Trim</th><th>Body</th><th>Name</th>
                  <th>Base price</th><th>Order</th><th>Active</th>
                </tr>
              </thead>
              <tbody>
                {structure.variants.map((variant) => (
                  <tr key={variant.variant_id}>
                    <td className="mono">{variant.variant_id}</td>
                    <td>{variant.trim_level}</td>
                    <td>{variant.body_style}</td>
                    <td>{variant.display_name}</td>
                    <td>{variant.base_price}</td>
                    <td>{variant.display_order}</td>
                    <td>{variant.active}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
          fieldGroups={editing.fieldGroups}
          saveFn={saveDraft}
          onSaved={saved}
          onCancel={() => setEditing(null)}
          saveLabel={editing.saveLabel}
          title={editing.title}
          target={editing.target}
        />
      )}
    </div>
  );
}