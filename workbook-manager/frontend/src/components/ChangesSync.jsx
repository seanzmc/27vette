import React, { useEffect, useMemo, useState } from "react";
import {
  CheckCheck, DatabaseBackup, FileDown, FileUp, PlayCircle, RefreshCcw,
  RotateCcw, ShieldCheck, StopCircle, TriangleAlert,
} from "lucide-react";
import { api } from "../api.js";

const TERMINAL = new Set([
  "applied", "cancelled", "manually_resolved_restored",
  "manually_resolved_applied", "abandoned_unknown",
]);

function compact(value, length = 16) {
  if (!value) return "—";
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

function latest(items = []) {
  return items[items.length - 1] || null;
}

function messages(attempt) {
  if (!attempt) return [];
  const result = attempt.result || {};
  const errors = (result.errors || []).map((item) =>
    typeof item === "string" ? item : (item.message || JSON.stringify(item))
  );
  if (attempt.exception_message) errors.unshift(
    `${attempt.exception_class || "Error"}: ${attempt.exception_message}`
  );
  return errors;
}

export default function ChangesSync({
  status, draftId, lifecycle, onChanged, onStartNew,
}) {
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState(null);
  const [actor, setActor] = useState("Workbook Manager operator");
  const [acceptedWarnings, setAcceptedWarnings] = useState([]);
  const [importReport, setImportReport] = useState(null);
  const [applyConfirmation, setApplyConfirmation] = useState("");

  const artifacts = lifecycle?.artifacts || {};
  const previewAttempt = latest(artifacts.preview_attempts);
  const approvalAttempt = latest(artifacts.approval_attempts);
  const applyAttempt = latest(artifacts.apply_attempts);
  const preview = previewAttempt?.result || null;
  const approval = approvalAttempt?.result || null;
  const changeSet = artifacts.changeset?.artifact || null;
  const draftState = lifecycle?.draft?.status || "new";
  const operations = lifecycle?.operations || [];
  const assetResolutions = artifacts.asset_resolutions || [];
  const assetIgnores = assetResolutions.filter((item) => item.resolution_kind === "ignore");
  const confirmableWarnings = preview?.warningPolicy?.confirmableIds || [];
  const visibleWarnings = preview?.warnings || [];
  const rebuild = applyAttempt?.result?.applyRebuild || null;

  useEffect(() => {
    setAcceptedWarnings((current) => current.filter(
      (warningId) => confirmableWarnings.includes(warningId)
    ));
  }, [preview?.previewFingerprint]); // eslint-disable-line

  const identityRows = useMemo(() => [
    ["Draft", lifecycle?.draft?.id || draftId],
    ["ChangeSet", changeSet?.changeSetId],
    ["Semantic fingerprint", changeSet?.semanticFingerprint],
    ["Preview fingerprint", preview?.previewFingerprint],
    ["Approval fingerprint", approval?.approvalFingerprint],
  ], [lifecycle, draftId, changeSet, preview, approval]);

  const run = async (label, action) => {
    setBusy(label);
    setNotice(null);
    try {
      await action();
      await onChanged();
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
    } finally {
      setBusy("");
    }
  };

  const canCancel = lifecycle && !TERMINAL.has(draftState)
    && !["applying", "workbook_state_unknown"].includes(draftState);
  const canPreview = [
    "changeset_emitted", "preview_retryable", "approval_repreview_required",
  ].includes(draftState);
  const canApprove = ["preview_ready", "approval_confirmation_required"].includes(draftState);
  const canApply = ["approved", "apply_retryable", "apply_restored_retryable"].includes(draftState);

  return (
    <div>
      <div className="draft-hero">
        <div>
          <div className="eyebrow">Durable workbook draft</div>
          <h2>Review the exact change before it can ever reach the workbook.</h2>
          <p>
            Edits are durable manager intent. Commit freezes one ChangeSet;
            preview runs the shared workbook gate; approval binds that exact preview.
          </p>
        </div>
        <div className="draft-state-card">
          <span className="muted">Current state</span>
          <strong>{draftState.replaceAll("_", " ")}</strong>
          <span className="mono faint" title={draftId}>{compact(draftId, 24)}</span>
        </div>
      </div>

      {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}
      {status?.projection?.blocking_findings > 0 && (
        <div className="notice err">
          Projection has {status.projection.blocking_findings} blocking finding(s).
          Draft authoring and lifecycle advancement remain fail-closed.
        </div>
      )}

      <div className="section-heading">Draft operations ({operations.length})</div>
      <div className="panel">
        {operations.length === 0 ? (
          <div className="empty">
            No operations yet. Edit a projected record in Form Structure or Model Operations.
          </div>
        ) : operations.map((operation) => (
          <div className="draft-operation" key={operation.id}>
            <div className="operation-heading">
              <span className={`op-tag ${operation.action}`}>{operation.action.toUpperCase()}</span>
              <strong>{operation.table_name}</strong>
              <span className="mono faint">
                {Object.entries(operation.entity_key || {}).map(([key, value]) => `${key}=${value}`).join(", ")}
              </span>
              <span className="spacer" />
              {(operation.model_context || []).map((model) => (
                <span className="chip blue" key={model}>{model}</span>
              ))}
            </div>
            <div className="lineage-row">
              <span>sheet <strong>{operation.source_sheet}</strong></span>
              <span>row <strong>{operation.source_row ?? "new"}</strong></span>
              <span>family <strong>{operation.family}</strong></span>
              <span className="mono" title={operation.physical_key}>
                physical {compact(operation.physical_key, 28)}
              </span>
            </div>
            <div className="field-diff">
              {Object.entries(operation.changed_fields || {}).map(([field, pair]) => (
                <React.Fragment key={field}>
                  <div className="field-name">{field}</div>
                  <div className="before-value">{pair.before === null ? <em>SQL NULL</em> : String(pair.before)}</div>
                  <div className="after-value">{pair.after === null ? <em>SQL NULL</em> : String(pair.after)}</div>
                </React.Fragment>
              ))}
            </div>
            {(operation.asset_resolutions || []).map((resolution) => (
              <div className="asset-evidence-summary" key={resolution.id}>
                <div>
                  <span className="chip blue">asset {resolution.resolution_kind.replaceAll("_", " ")}</span>
                  <strong>{resolution.evidence?.source_status || "asset resolution"}</strong>
                  <span>{resolution.candidate_source || "manual authority"}</span>
                </div>
                <p>{resolution.candidate_reason || "Explicit operator-authored presentation change."}</p>
                <div className="lineage-row">
                  <span>item <strong className="mono">{compact(resolution.item_id, 20)}</strong></span>
                  <span>reconciliation <strong className="mono">{compact(resolution.reconciliation_sha256, 20)}</strong></span>
                  <span>inventory <strong className="mono">{compact(resolution.media_inventory_sha256, 20)}</strong></span>
                  <span>coverage <strong>{resolution.evidence?.coverage?.kind || "n/a"}</strong></span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {assetIgnores.length > 0 && (
        <>
          <div className="section-heading">Operational asset dispositions ({assetIgnores.length})</div>
          <div className="panel">
            {assetIgnores.map((resolution) => (
              <div className="draft-operation" key={resolution.id}>
                <div className="operation-heading">
                  <span className="op-tag update">IGNORE</span>
                  <strong>{resolution.evidence?.media_url || resolution.media_url}</strong>
                </div>
                <div className="lineage-row">
                  <span>item <strong className="mono">{compact(resolution.item_id, 20)}</strong></span>
                  <span>inventory <strong className="mono">{compact(resolution.media_inventory_sha256, 20)}</strong></span>
                  <span>changed inventory returns this item to review</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="section-heading">Lifecycle actions</div>
      <div className="panel">
        <div className="panel-body">
          <div className="toolbar lifecycle-actions">
            {draftState === "draft" && (
              <button
                className="btn primary"
                disabled={!operations.length || !!busy}
                onClick={() => run("commit", () => api.commitDraft(draftId))}
              >
                <CheckCheck size={15} /> Freeze ChangeSet
              </button>
            )}
            {canPreview && (
              <button
                className="btn primary"
                disabled={!!busy}
                onClick={() => run("preview", () => api.previewDraft(draftId))}
              >
                {draftState === "changeset_emitted"
                  ? <ShieldCheck size={15} />
                  : <RotateCcw size={15} />}
                {draftState === "changeset_emitted" ? "Run Workbook Preview" : "Retry Preview"}
              </button>
            )}
            {canApprove && (
              <button
                className="btn primary"
                disabled={!!busy || !actor.trim()}
                onClick={() => run("approve", () => api.approveDraft(draftId, {
                  actor: actor.trim(), warning_ids: acceptedWarnings,
                }))}
              >
                <CheckCheck size={15} /> Approve Exact Preview
              </button>
            )}
            {canApply && (
              <button
                className="btn primary"
                disabled={!!busy || !actor.trim() || applyConfirmation !== "APPLY AND REBUILD"}
                onClick={() => run("apply_rebuild", async () => {
                  const attempt = await api.applyRebuildDraft(draftId, {
                    actor: actor.trim(), confirm: applyConfirmation,
                  });
                  const state = attempt.result?.applyRebuild?.status || attempt.manager_state;
                  setNotice({
                    kind: attempt.manager_state === "applied" ? "ok" : "err",
                    text: `Apply and Rebuild finished: ${state.replaceAll("_", " ")}.`,
                  });
                })}
              >
                {draftState === "approved" ? <PlayCircle size={15} /> : <RotateCcw size={15} />}
                {draftState === "approved" ? "Apply and Rebuild" : "Retry Apply and Rebuild"}
              </button>
            )}
            {canCancel && (
              <button
                className="btn danger"
                disabled={!!busy}
                onClick={() => run("cancel", () => api.cancelDraft(draftId))}
              >
                <StopCircle size={15} /> Cancel Draft
              </button>
            )}
            {TERMINAL.has(draftState) && (
              <button className="btn" disabled={!!busy} onClick={onStartNew}>
                Start New Draft
              </button>
            )}
            {busy && <span className="muted">{busy.replaceAll("_", " ")}…</span>}
          </div>
          {canApprove && (
            <div className="approval-box">
              <label>
                Operator
                <input className="text" value={actor} onChange={(event) => setActor(event.target.value)} />
              </label>
              {confirmableWarnings.map((warningId) => (
                <label className="warning-check" key={warningId}>
                  <input
                    type="checkbox"
                    checked={acceptedWarnings.includes(warningId)}
                    onChange={(event) => setAcceptedWarnings((current) => event.target.checked
                      ? [...new Set([...current, warningId])]
                      : current.filter((item) => item !== warningId))}
                  />
                  Accept confirmable warning <span className="mono">{warningId}</span>
                </label>
              ))}
            </div>
          )}
          {canApply && (
            <div className="apply-confirmation">
              <div className="notice warn">
                <TriangleAlert size={16} /> This action writes the exact approved ChangeSet, then regenerates and publishes the derived local model outputs. It does not deploy or submit to a dealer.
              </div>
              <label>
                <span>Type <span className="mono">APPLY AND REBUILD</span> to continue</span>
                <input
                  className="text mono"
                  value={applyConfirmation}
                  onChange={(event) => setApplyConfirmation(event.target.value)}
                  placeholder="APPLY AND REBUILD"
                />
              </label>
            </div>
          )}
          {draftState === "workbook_state_unknown" && (
            <div className="manual-recovery notice err">
              <strong>Manual recovery required.</strong>
              <span>No retry or cancellation is safe. Inspect the immutable evidence, then record only what you have independently verified.</span>
              <div className="toolbar">
                {["restored", "applied", "abandoned_unknown"].map((resolution) => (
                  <button
                    className="btn danger"
                    disabled={!!busy || !actor.trim()}
                    key={resolution}
                    onClick={() => {
                      if (!window.confirm(`Record manual resolution: ${resolution.replaceAll("_", " ")}?`)) return;
                      run("manual_resolution", () => api.resolveUnknownDraft(draftId, {
                        actor: actor.trim(), resolution,
                        evidence: { note: "Recorded from Workbook Manager recovery controls." },
                      }));
                    }}
                  >
                    {resolution.replaceAll("_", " ")}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {rebuild && (
        <>
          <div className="section-heading">Apply and Rebuild result</div>
          <div className="apply-state-grid">
            {[
              ["Workbook", rebuild.workbook],
              ["Projection", rebuild.projection],
              ["Generated contracts", rebuild.generated_contracts],
              ["Publication", rebuild.publication],
            ].map(([label, evidence]) => (
              <div className="panel panel-body" key={label}>
                <span className="muted">{label}</span>
                <strong>{evidence?.state || "unknown"}</strong>
                {label === "Generated contracts" && (
                  <span>{rebuild.affected_models?.join(", ") || "no models"}</span>
                )}
                {label === "Publication" && evidence?.changed && (
                  <span>data.js cache {evidence.cache_version_before} → {evidence.cache_version_after}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      <div className="section-heading">Exact lifecycle evidence</div>
      <div className="evidence-grid">
        <div className="panel panel-body">
          <strong>Bound identities</strong>
          <dl className="identity-list">
            {identityRows.map(([label, value]) => (
              <React.Fragment key={label}>
                <dt>{label}</dt>
                <dd className="mono" title={value || ""}>{compact(value, 28)}</dd>
              </React.Fragment>
            ))}
          </dl>
        </div>
        <div className="panel panel-body">
          <strong>Warnings &amp; failures</strong>
          {!visibleWarnings.length && !messages(previewAttempt).length && !messages(approvalAttempt).length
            ? <p className="muted">No recorded warnings or failures.</p>
            : (
              <ul className="error-list compact-list">
                {visibleWarnings.map((warning, index) => (
                  <li className="warning" key={`warning-${index}`}>
                    {warning.id ? `${warning.id}: ` : ""}{warning.message || String(warning)}
                  </li>
                ))}
                {[...messages(previewAttempt), ...messages(approvalAttempt), ...messages(applyAttempt)]
                  .map((message, index) => <li key={`error-${index}`}>{message}</li>)}
              </ul>
            )}
        </div>
      </div>

      {(previewAttempt || approvalAttempt || applyAttempt || artifacts.manual_resolutions?.length > 0) && (
        <div className="panel artifact-history">
          <div className="panel-head"><strong>Immutable attempt history</strong></div>
          {[...(artifacts.preview_attempts || []).map((item) => ["Preview", item]),
            ...(artifacts.approval_attempts || []).map((item) => ["Approval", item]),
            ...(artifacts.apply_attempts || []).map((item) => ["Apply", item])]
            .map(([kind, item]) => (
              <details key={`${kind}-${item.id}`}>
                <summary>
                  {kind} · {item.manager_state} · <span className="mono">{compact(item.id)}</span>
                </summary>
                <pre>{JSON.stringify(item, null, 2)}</pre>
              </details>
            ))}
          {(artifacts.manual_resolutions || []).map((item) => (
            <details key={item.id} open>
              <summary>Manual resolution · {item.manager_state}</summary>
              <pre>{JSON.stringify(item, null, 2)}</pre>
            </details>
          ))}
        </div>
      )}

      <div className="section-heading">Projection tools</div>
      <div className="panel">
        <div className="panel-body toolbar">
          <button
            className="btn"
            disabled={!!busy || !status?.projection?.reimport_allowed}
            onClick={() => run("import", async () => setImportReport(await api.runImport()))}
          >
            <FileUp size={15} /> Re-Import Workbook
          </button>
          <button
            className="btn"
            disabled={!!busy || status?.projection?.state !== "current"}
            onClick={() => run("export", async () => {
              const result = await api.exportWorkbook();
              setNotice({ kind: "ok", text: `Disposable comparison exported: ${result.path}` });
            })}
          >
            <FileDown size={15} /> Export Disposable Comparison
          </button>
          <button className="btn" disabled={!!busy} onClick={() => run("backup", async () => {
            const result = await api.backup();
            setNotice({ kind: "ok", text: `Database backup: ${result.path}` });
          })}>
            <DatabaseBackup size={15} /> Backup Manager State
          </button>
          <button className="btn" disabled={!!busy} onClick={() => run("refresh", async () => {})}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>
        {importReport && (
          <div className="panel-body">
            <div className={`notice ${importReport.run?.status === "imported" ? "ok" : "err"}`}>
              Import {importReport.run?.status || importReport.status} · {importReport.issues?.length || 0} issue(s)
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
