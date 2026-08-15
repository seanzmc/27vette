import React, { useEffect, useState } from "react";
import { ChevronRight, Layers, Pencil } from "lucide-react";
import { api } from "../api.js";
import { humanize } from "../naming.js";
import RecordForm from "./RecordForm.jsx";

export default function FormStructure({
  models, modelKey, setModelKey, draftId, draftMutable, onChanged,
}) {
  const [structure, setStructure] = useState(null);
  const [editing, setEditing] = useState(null); // {table, mode, initial, schema}
  const [error, setError] = useState("");

  const load = async (key) => {
    try {
      setStructure(await api.structure(key));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { if (modelKey) load(modelKey); }, [modelKey]);

  const startEdit = async (table, initial) => {
    const schema = await api.schema(table, modelKey);
    setEditing({ table, mode: initial ? "edit" : "add", initial, schema });
  };

  const saved = async (operation) => {
    setEditing(null);
    await load(modelKey);
    onChanged({ draft: Boolean(operation) });
  };

  const saveDraft = (payload) => api.saveDraftOperation(draftId, {
    ...payload,
    actor: "workbook-manager-ui",
    session_id: "browser",
  });

  return (
    <div>
      <div className="section-heading"><Layers size={14} /> Model Activation Sequence</div>
      <div className="model-grid">
        {models.map((m) => (
          <button
            key={m.model_key}
            className={`model-card ${m.model_key === modelKey ? "selected" : ""} ${m.scaffold ? "scaffold" : ""}`}
            onClick={() => setModelKey(m.model_key)}
          >
            <div className="name">
              {m.label}
              <span className="faint mono">{m.model_year}</span>
            </div>
            <div className="tags">
              <span className={`chip ${m.active === "True" ? "on" : "off"}`}>
                {m.active === "True" ? "Active" : "Scaffold"}
              </span>
              {m.promoted_to_runtime === "True" && <span className="chip blue">Runtime</span>}
              {m.default_model === "True" && <span className="chip warn">Default</span>}
            </div>
          </button>
        ))}
      </div>

      <div className="toolbar" style={{ marginBottom: 14 }}>
        <button
          className="btn small"
          disabled={!draftMutable || !models.find((model) => model.model_key === modelKey)}
          onClick={async () => {
            const model = models.find((item) => item.model_key === modelKey);
            if (model) await startEdit("models", model);
          }}
        >
          <Pencil size={14} /> Edit model metadata &amp; Vehicle Setup copy
        </button>
        {!draftMutable && (
          <span className="muted">This draft is locked; start a new draft to edit.</span>
        )}
      </div>

      {error && <div className="notice err">{error}</div>}

      {structure && (
        <>
          <div className="section-heading">
            <ChevronRight size={14} /> Runtime Steps &amp; Interface Sections — {humanize(modelKey)}
          </div>
          <div className="panel">
            {structure.steps.length === 0 && (
              <div className="empty">
                No workbook-owned runtime steps for this model (unpromoted
                scaffolds have empty presentation sheets).
              </div>
            )}
            {structure.steps.map((s, i) => (
              <div className="step-row" key={s.step_key}>
                <span className="step-num">{s.runtime_order || i + 1}</span>
                <div className="step-main">
                  <div className="label">
                    {s.display_name}
                    {s.active !== "True" && (
                      <span className="chip off" style={{ marginLeft: 6 }}>inactive</span>
                    )}
                  </div>
                  <div className="key">{s.step_key}</div>
                </div>
                <div className="step-sections">
                  {s.sections.length === 0 ? (
                    <span className="faint" style={{ fontSize: 12 }}>
                      no sections mapped
                    </span>
                  ) : (
                    s.sections.map((sec) => (
                      <span
                        key={sec.section_id}
                        className={`chip ${sec.active === "True" ? "" : "off"}`}
                        title={`${sec.section_id} · order ${sec.section_display_order}`}
                      >
                        {sec.display_name}
                      </span>
                    ))
                  )}
                </div>
                <button
                  className="icon-btn"
                  title="Edit step"
                  disabled={!draftMutable}
                  onClick={() => startEdit("form_steps", s)}
                >
                  <Pencil size={14} />
                </button>
              </div>
            ))}
          </div>

          <div className="section-heading">Section Presentation Order</div>
          <div className="panel">
            <div className="panel-head">
              <span className="muted">
                Workbook-owned display order, labels, and conditional
                visibility (display_behavior) per section.
              </span>
              <button className="btn small" disabled={!draftMutable} onClick={() => startEdit("section_presentation", null)}>
                Add Section Presentation
              </button>
            </div>
            <table className="data">
              <thead>
                <tr>
                  <th>Order</th><th>Section</th><th>Section ID</th><th>Step</th>
                  <th>Behavior</th><th>Active</th><th></th>
                </tr>
              </thead>
              <tbody>
                {structure.section_presentation.map((p) => (
                  <tr key={p.section_id}>
                    <td>{p.section_display_order}</td>
                    <td>{p.display_name}</td>
                    <td className="mono faint">{p.section_id}</td>
                    <td className="mono faint">{p.step_key}</td>
                    <td>{p.display_behavior || <span className="faint">—</span>}</td>
                    <td>
                      <span className={`chip ${p.active === "True" ? "on" : "off"}`}>
                        {p.active}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button className="icon-btn" disabled={!draftMutable} onClick={() => startEdit("section_presentation", p)}>
                          <Pencil size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="section-heading">Variants</div>
          <div className="panel">
            <table className="data">
              <thead>
                <tr>
                  <th>Variant</th><th>Trim</th><th>Body</th><th>Name</th>
                  <th>Base Price</th><th>Order</th><th>Active</th>
                </tr>
              </thead>
              <tbody>
                {structure.variants.map((v) => (
                  <tr key={v.variant_id}>
                    <td className="mono">{v.variant_id}</td>
                    <td>{v.trim_level}</td>
                    <td>{v.body_style}</td>
                    <td>{v.display_name}</td>
                    <td>{v.base_price}</td>
                    <td>{v.display_order}</td>
                    <td>
                      <span className={`chip ${v.active === "True" ? "on" : "off"}`}>
                        {v.active}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {editing && (
        <div style={{ marginTop: 14 }}>
          <RecordForm
            key={`${editing.table}-${editing.mode}-${editing.initial?.id ?? "new"}`}
            schema={editing.schema}
            mode={editing.mode}
            initial={editing.initial}
            modelKey={modelKey}
            saveFn={saveDraft}
            onSaved={saved}
            onCancel={() => setEditing(null)}
          />
        </div>
      )}
    </div>
  );
}
