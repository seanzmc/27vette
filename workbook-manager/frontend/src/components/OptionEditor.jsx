import React, { useEffect, useMemo, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { api } from "../api.js";
import {
  editorTarget,
  entityLabel,
  initialDraftFromDetail,
  relationshipImpact,
} from "../optionEditorModel.js";
import RecordForm from "./RecordForm.jsx";
import EditorShell from "./EditorShell.jsx";

// These are contextual intent headings only. The schema still owns every
// included field, renderer kind, label, blank rule, and validation constraint.
const OPTION_FIELD_GROUPS = [
  {
    label: "Identity and customer copy",
    fields: ["option_id", "rpo", "option_name", "description", "detail_raw"],
  },
  {
    label: "Form placement and display",
    fields: ["section_id", "selectable", "display_order", "display_behavior", "active"],
  },
  { label: "Base pricing", fields: ["price"] },
];

// Post-Save state for this option: the effective draft overlay plus direct
// impact, both derived from durable evidence rather than optimistic local
// guesses.
function DraftOverlay({ detail, operation, impact }) {
  const changed = Object.entries(operation?.changed_fields || {});
  return (
    <div className="option-editor-overlay" data-testid="option-draft-overlay">
      <h3>Draft overlay</h3>
      {changed.length === 0 ? (
        <p className="muted">No effective draft changes remain for this option.</p>
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
      <h3>Direct impact</h3>
      <div className="detail-facts">
        <span><strong>Availability rows</strong>{impact.availability}</span>
        <span><strong>Groups</strong>{impact.groups}</span>
        <span><strong>Rules</strong>{impact.rules}</span>
        <span><strong>Pricing rules</strong>{impact.pricingRules}</span>
        <span><strong>Variant overrides</strong>{impact.variantOverrides}</span>
        <span><strong>Default rules</strong>{impact.defaultRules}</span>
        <span><strong>Images</strong>{impact.images}</span>
      </div>
      <p className="muted">
        Saved to the durable draft only. Review the complete graph in Review &amp;
        Apply; the workbook changes only through Apply and Rebuild.
      </p>
    </div>
  );
}

export default function OptionEditor({
  detail, modelKey, draftId, draftMutable, onClose, onChanged,
}) {
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState("");
  const [savedOperation, setSavedOperation] = useState(null);
  const [hasSaved, setHasSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let current = true;
    setSchema(null);
    setSavedOperation(null);
    setHasSaved(false);
    setError("");
    api.schema("options", modelKey).then((spec) => {
      if (current) setSchema(spec);
    }).catch((e) => {
      if (current) setError(e.message);
    });
    return () => { current = false; };
  }, [modelKey]);

  const target = useMemo(() => editorTarget(detail), [detail]);
  const initial = useMemo(
    () => initialDraftFromDetail(detail),
    [detail],
  );
  const impact = useMemo(() => relationshipImpact(detail), [detail]);
  const label = useMemo(() => entityLabel(detail), [detail]);

  const saveDraft = async (payload) => {
    if (!draftMutable || !draftId) {
      throw new Error("The active draft is locked; start a new draft to edit.");
    }
    setBusy(true);
    try {
      const operation = await api.saveDraftOperation(draftId, {
        ...payload,
        actor: "workbook-manager-ui",
        session_id: "browser",
      });
      setSavedOperation(operation);
      setHasSaved(true);
      Promise.resolve(onChanged?.()).catch((refreshError) => {
        setError(`The option change was saved, but screen status could not refresh: ${refreshError.message}`);
      });
      return operation;
    } finally {
      setBusy(false);
    }
  };

  if (hasSaved) return (
    <EditorShell
      title={`Edit option · ${label}`}
      subtitle="Changes are saved to the durable draft only. The workbook is not changed here."
      target={`${label} · ${target.lineage.source_sheet || "options"}`}
      dirty={false}
      busy={busy}
      onRequestClose={onClose}
      footer={(requestClose) =>
        <>
          <button type="button" className="btn small" onClick={() => setHasSaved(false)}>
            <ArrowLeft size={14} /> Keep editing
          </button>
          <button type="button" className="btn primary small" onClick={requestClose}>
            Close
          </button>
        </>
      }
    >
      {error && <div className="notice err" role="alert">{error}</div>}
      <DraftOverlay detail={detail} operation={savedOperation} impact={impact} />
    </EditorShell>
  );

  if (!schema) return (
    <EditorShell
      title={`Edit option · ${label}`}
      subtitle="Loading registry controls for this option."
      target={`${label} · ${target.lineage.source_sheet || "options"}`}
      dirty={false}
      busy={false}
      onRequestClose={onClose}
    >
      {error ? <div className="notice err" role="alert">{error}</div> : <p>Loading editor…</p>}
    </EditorShell>
  );

  return (
    <RecordForm
      key={`${target.key.option_id}`}
      schema={schema}
      mode="edit"
      initial={initial.draft}
      modelKey={modelKey}
      fieldGroups={OPTION_FIELD_GROUPS}
      saveFn={saveDraft}
      onSaved={(operation) => {
        setSavedOperation(operation);
        setHasSaved(true);
      }}
      onCancel={onClose}
      saveLabel="Save option change to draft"
      title={`Edit option · ${label}`}
      target={`${label} · ${target.lineage.source_sheet || "options"}`}
    />
  );
}
