import React, { useEffect, useState } from "react";
import {
  CheckCheck, DatabaseBackup, FileDown, FileUp,
  RefreshCcw, ShieldCheck, Undo2,
} from "lucide-react";
import { api } from "../api.js";

export default function ChangesSync({ status, onChanged }) {
  const [staged, setStaged] = useState([]);
  const [validation, setValidation] = useState(null);
  const [commitResult, setCommitResult] = useState(null);
  const [dryRun, setDryRun] = useState(null);
  const [importReport, setImportReport] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState("");

  const refresh = async () => {
    const c = await api.changes("staged");
    setStaged(c.changes);
    onChanged();
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line

  const run = async (label, fn) => {
    setBusy(label);
    setNotice(null);
    try {
      return await fn();
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
      return null;
    } finally {
      setBusy("");
    }
  };

  const unsynced = status?.unsynced_committed_changes ?? 0;

  return (
    <div>
      <div className="section-heading">Staged Changes ({staged.length})</div>
      <div className="panel">
        <div className="panel-head">
          <span className="muted">
            Staged changes live outside the database tables until committed;
            undo removes them without a trace in the audit history.
          </span>
          <div className="toolbar">
            <button
              className="btn small"
              disabled={!staged.length || !!busy}
              onClick={() => run("validate", async () => setValidation(await api.validateChanges()))}
            >
              <ShieldCheck size={14} /> Validate All
            </button>
            <button
              className="btn primary small"
              disabled={!staged.length || !!busy}
              onClick={() => run("commit", async () => {
                const r = await api.commit("workbook-manager-ui");
                setCommitResult(r);
                setValidation(r.validation ?? null);
                await refresh();
              })}
            >
              <CheckCheck size={14} /> Validate &amp; Commit
            </button>
          </div>
        </div>
        {staged.length === 0 ? (
          <div className="empty">Nothing staged. Edits from both workspaces queue here.</div>
        ) : (
          staged.map((c) => {
            const errs = validation?.results?.find((r) => r.change_id === c.id)?.errors || [];
            return (
              <div className="change-row" key={c.id}>
                <span className={`op-tag ${c.op}`}>{c.op.toUpperCase()}</span>
                <span className="mono">{c.table_name}</span>
                {c.model_id && <span className="chip blue">{c.model_id}</span>}
                <span className="mono faint">
                  {Object.entries(c.entity_key || {}).map(([k, v]) => `${k}=${v}`).join(", ")}
                </span>
                {errs.length > 0 && (
                  <span className="chip err">{errs.length} validation error(s)</span>
                )}
                <span className="spacer" />
                <span className="faint mono">{c.ts}</span>
                <button
                  className="icon-btn danger"
                  title="Undo (discard staged change)"
                  onClick={() => run("undo", async () => { await api.discard(c.id); await refresh(); })}
                >
                  <Undo2 size={14} />
                </button>
              </div>
            );
          })
        )}
        {validation && !validation.ok && (
          <div className="panel-body">
            <div className="notice err">
              Batch validation failed — fix or undo the flagged changes before commit.
            </div>
            <ul className="error-list">
              {validation.results.flatMap((r) =>
                r.errors.map((e, i) => (
                  <li key={`${r.change_id}-${i}`}>
                    #{r.change_id} · {e.table}{e.model_id ? ` (${e.model_id})` : ""}
                    {e.field ? ` · ${e.field}` : ""} — {e.message}
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
        {commitResult && (
          <div className="panel-body">
            <div className={`notice ${commitResult.ok ? "ok" : "err"}`}>
              {commitResult.ok
                ? `Committed ${commitResult.committed} change(s) to the database. Audit rows written; workbook not yet touched.`
                : `Commit blocked: ${commitResult.status}`}
            </div>
          </div>
        )}
      </div>

      <div className="section-heading">Workbook Sync Preview ({unsynced} committed change(s) pending; write disabled)</div>
      <div className="panel">
        <div className="panel-body">
          <div className="toolbar">
            <button
              className="btn"
              disabled={!unsynced || !!busy}
              onClick={() => run("dryrun", async () => {
                setDryRun(await api.sync({ write: false }));
              })}
            >
              <ShieldCheck size={15} /> {busy === "dryrun" ? "Running gate…" : "Dry-Run Sync"}
            </button>
            <span className="muted">
              Dry-run pushes pending changes through the repo's gated pipeline
              (lock check, batch validation, temp-copy apply, package + schema
              validation) without writing. Slow is normal.
            </span>
          </div>

          {dryRun && (
            <div className={`notice ${dryRun.status === "validated" ? "ok" : "err"}`}>
              Dry-run: <strong>{dryRun.status}</strong> · {dryRun.opCount ?? 0} op(s)
              {dryRun.errors?.length > 0 && (
                <ul className="error-list">
                  {dryRun.errors.map((e, i) => <li key={i}>{String(e)}</li>)}
                </ul>
              )}
              {dryRun.warnings?.length > 0 && (
                <ul className="error-list">
                  {dryRun.warnings.map((w, i) => (
                    <li key={i} style={{ color: "var(--accent)", borderColor: "rgba(245,185,66,.4)", background: "rgba(245,185,66,.07)" }}>
                      ⚠ {w.id}: {w.message}
                    </li>
                  ))}
                </ul>
              )}
              {dryRun.skipped?.length > 0 && (
                <div className="muted" style={{ marginTop: 6 }}>
                  {dryRun.skipped.length} change(s) skipped (no workbook write path).
                </div>
              )}
            </div>
          )}

        </div>
      </div>

      <div className="section-heading">Workbook &amp; Database Tools</div>
      <div className="panel">
        <div className="panel-body toolbar">
          <button
            className="btn"
            disabled={!!busy || status?.projection?.active}
            title={status?.projection?.active
              ? "Re-import is disabled until candidate promotion is implemented."
              : "Import the workbook into an empty projection."}
            onClick={() => run("import", async () => {
              const r = await api.runImport();
              setImportReport(r);
              await refresh();
            })}
          >
            <FileUp size={15} /> Re-Import Workbook
          </button>
          <button
            className="btn"
            disabled={!!busy || status?.projection?.state !== "current"}
            title={status?.projection?.state !== "current"
              ? "Export requires a current verified projection."
              : "Create a disposable comparison workbook."}
            onClick={() => run("export", async () => {
              const r = await api.exportWorkbook();
              setNotice({ kind: "ok", text: `Disposable comparison workbook exported: ${r.path}` });
            })}
          >
            <FileDown size={15} /> Export Disposable Comparison
          </button>
          <button
            className="btn"
            disabled={!!busy}
            onClick={() => run("backup", async () => {
              const r = await api.backup();
              setNotice({ kind: "ok", text: `Database backup: ${r.path}` });
            })}
          >
            <DatabaseBackup size={15} /> Backup Database
          </button>
          <button className="btn" disabled={!!busy} onClick={() => run("refresh", refresh)}>
            <RefreshCcw size={15} /> Refresh
          </button>
        </div>
        {notice && <div className="panel-body"><div className={`notice ${notice.kind}`}>{notice.text}</div></div>}
        {importReport && (
          <div className="panel-body">
            <div className={`notice ${importReport.run.status === "imported" ? "ok" : "warn"}`}>
              Import {importReport.run.status} · {importReport.issues.length} issue(s)
            </div>
            {importReport.issues.length > 0 && (
              <ul className="error-list">
                {importReport.issues.slice(0, 50).map((i) => (
                  <li
                    key={i.id}
                    style={i.severity === "warning"
                      ? { color: "var(--accent)", borderColor: "rgba(245,185,66,.4)", background: "rgba(245,185,66,.07)" }
                      : undefined}
                  >
                    [{i.severity}] {i.category} · {i.sheet}
                    {i.src_row ? `:${i.src_row}` : ""}
                    {i.entity_key ? ` · ${i.entity_key}` : ""} — {i.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
