import React, { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, History } from "lucide-react";
import { api } from "../api.js";

const PAGE_SIZE = 25;

function readableStatus(value) {
  return String(value || "").replaceAll("_", " ");
}

export default function HistoryView({ models, onOpenDraft }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [statuses, setStatuses] = useState([]);
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [legacyRows, setLegacyRows] = useState([]);
  const [legacyTotal, setLegacyTotal] = useState(0);
  // Request identity: only the response for the newest filter/page state may
  // update the view, so a slower earlier response cannot overwrite it.
  const requestRef = React.useRef(0);

  const load = async () => {
    const requestId = ++requestRef.current;
    try {
      const response = await api.workflowHistory({
        model, status, limit: PAGE_SIZE, offset,
      });
      if (requestId !== requestRef.current) return;
      setRows(response.history);
      setTotal(response.total);
      setStatuses(response.available_statuses);
      setError("");
    } catch (requestError) {
      if (requestId !== requestRef.current) return;
      setRows([]);
      setError(`Workflow history could not be loaded: ${requestError.message}`);
    }
  };

  useEffect(() => { load(); }, [model, status, offset]); // eslint-disable-line
  useEffect(() => {
    api.history({ limit: 200 })
      .then((response) => {
        setLegacyRows(response.history);
        setLegacyTotal(response.total);
      })
      .catch(() => {
        setLegacyRows([]);
        setLegacyTotal(0);
      });
  }, []);

  const updateModel = (value) => { setModel(value); setOffset(0); };
  const updateStatus = (value) => { setStatus(value); setOffset(0); };

  return (
    <section className="workflow-history">
      <div className="section-heading"><History size={14} /> Workflow history</div>
      <p className="muted">
        Durable validation, approval, Apply and Rebuild, cancellation, and recovery outcomes.
      </p>
      <div className="panel">
        <div className="panel-head">
          <div className="toolbar">
            <label>Model
              <select className="select" value={model}
                onChange={(event) => updateModel(event.target.value)}>
                <option value="">All affected models</option>
                {models.map((item) => (
                  <option key={item.model_key} value={item.model_key}>{item.label}</option>
                ))}
              </select>
            </label>
            <label>Outcome
              <select className="select" value={status}
                onChange={(event) => updateStatus(event.target.value)}>
                <option value="">All recorded outcomes</option>
                {statuses.map((item) => (
                  <option key={item} value={item}>{readableStatus(item)}</option>
                ))}
              </select>
            </label>
          </div>
          <span className="muted">{total} workflow record(s)</span>
        </div>
        {error ? (
          <div className="notice err">{error} <button className="btn" onClick={load}>Retry</button></div>
        ) : rows.length === 0 ? (
          <div className="empty">No durable workflow outcomes match these filters.</div>
        ) : rows.map((record) => (
          <article className="workflow-history-record" key={record.draft_id}>
            <div className="workflow-history-heading">
              <div>
                <strong>{record.outcome.summary}</strong>
                <div className="muted">
                  {record.actor || "Unknown actor"} · {record.updated_ts} · {record.operation_count} operation(s)
                </div>
              </div>
              <span className={`chip ${record.status === "applied" ? "on" : record.outcome.error ? "err" : "warn"}`}>
                {readableStatus(record.status)}
              </span>
            </div>
            <div className="status-surfaces">
              {record.affected_models.map((item) => <span className="chip blue" key={item}>{item}</span>)}
              {record.outcome.generation_state && <span className="chip">Generated: {record.outcome.generation_state}</span>}
              {record.outcome.publication_state && <span className="chip">Published: {record.outcome.publication_state}</span>}
              {record.outcome.rollback_state && <span className="chip">Rollback: {record.outcome.rollback_state}</span>}
            </div>
            {record.outcome.error && <div className="notice err">{record.outcome.error}</div>}
            <dl className="identity-list">
              <dt>Draft</dt><dd className="mono">{record.draft_id}</dd>
              <dt>Base workbook</dt><dd className="mono">{record.workbook.base_sha256 || "—"}</dd>
              {record.workbook.after_sha256 && <><dt>Saved workbook</dt><dd className="mono">{record.workbook.after_sha256}</dd></>}
            </dl>
            <div className="toolbar">
              <button className="btn" type="button" onClick={() => onOpenDraft(record.draft_id)}>
                Open exact draft
              </button>
            </div>
            <details className="technical-details">
              <summary>Technical evidence</summary>
              <pre>{JSON.stringify(record.technical_evidence, null, 2)}</pre>
            </details>
          </article>
        ))}
        <div className="history-pagination">
          <button className="btn" type="button" disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            <ChevronLeft size={14} /> Newer
          </button>
          <span className="muted">{total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} of ${total}` : "0 records"}</span>
          <button className="btn" type="button" disabled={offset + PAGE_SIZE >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}>
            Older <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <details className="panel legacy-history">
        <summary>Legacy staging history ({legacyTotal})</summary>
        <p className="muted">
          Read-only evidence from the retired staging/sync workflow. These rows are not included in Workflow history totals.
        </p>
        {legacyRows.length === 0 ? (
          <div className="empty">No legacy staging rows.</div>
        ) : legacyRows.map((record) => (
          <div className="change-row" key={record.id}>
            <span className={`op-tag ${record.op}`}>{record.op.toUpperCase()}</span>
            <span className="mono">{record.entity_type}</span>
            <span className="mono faint">{record.entity_id}</span>
            {record.model_id && <span className="chip blue">{record.model_id}</span>}
            <span className="spacer" />
            <span className="faint mono">{record.ts}</span>
          </div>
        ))}
      </details>
    </section>
  );
}
