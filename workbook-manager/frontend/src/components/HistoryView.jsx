import React, { useEffect, useState } from "react";
import { History } from "lucide-react";
import { api } from "../api.js";

export default function HistoryView({ models }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [modelKey, setModelKey] = useState("");
  const [syncStatus, setSyncStatus] = useState("");
  const [expanded, setExpanded] = useState(null);

  const load = async (selectedModel = modelKey, s = syncStatus) => {
    const r = await api.history({
      model_key: selectedModel,
      sync_status: s,
      limit: 200,
    });
    setRows(r.history);
    setTotal(r.total);
  };

  useEffect(() => { load(); }, [modelKey, syncStatus]); // eslint-disable-line

  return (
    <div>
      <div className="section-heading"><History size={14} /> Change History (append-only audit)</div>
      <div className="panel">
        <div className="panel-head">
          <div className="toolbar">
            <select className="select" style={{ width: 180 }} value={modelKey}
              onChange={(e) => setModelKey(e.target.value)}>
              <option value="">All models</option>
              {models.map((m) => (
                <option key={m.model_key} value={m.model_key}>{m.label}</option>
              ))}
            </select>
            <select className="select" style={{ width: 180 }} value={syncStatus}
              onChange={(e) => setSyncStatus(e.target.value)}>
              <option value="">Any sync status</option>
              <option value="pending">Pending sync</option>
              <option value="synced">Synced</option>
              <option value="sync_failed">Sync failed</option>
              <option value="n/a">No workbook path</option>
            </select>
          </div>
          <span className="muted">{total} record(s)</span>
        </div>
        {rows.length === 0 ? (
          <div className="empty">No committed changes yet.</div>
        ) : (
          rows.map((h) => (
            <div key={h.id}>
              <div
                className="change-row"
                style={{ cursor: "pointer" }}
                onClick={() => setExpanded(expanded === h.id ? null : h.id)}
              >
                <span className={`op-tag ${h.op}`}>{h.op.toUpperCase()}</span>
                <span className="mono">{h.table_role}</span>
                <span className="chip mono">SQL · {h.sql_table}</span>
                <span className="mono faint">{h.entity_id}</span>
                {h.model_key && <span className="chip blue">{h.model_key}</span>}
                <span className={`chip ${h.sync_status === "synced" ? "on" : h.sync_status === "pending" ? "warn" : h.sync_status === "sync_failed" ? "err" : ""}`}>
                  {h.sync_status}
                </span>
                <span className="spacer" />
                {h.src_sheet && (
                  <span className="faint mono">{h.src_sheet}{h.src_row ? `:${h.src_row}` : ""}</span>
                )}
                <span className="faint mono">{h.ts}</span>
                {h.actor && <span className="faint">{h.actor}</span>}
              </div>
              {expanded === h.id && (
                <div className="panel-body">
                  <div className="diff-grid">
                    <div className="head">Field</div>
                    <div className="head">Previous</div>
                    <div className="head">New</div>
                    {Array.from(
                      new Set([
                        ...Object.keys(h.old || {}),
                        ...Object.keys(h.new || {}),
                      ])
                    )
                      .filter((k) => ![
                        "id", "src_sheet", "src_row", "model_key",
                      ].includes(k))
                      .map((k) => {
                        const a = String(h.old?.[k] ?? "");
                        const b = String(h.new?.[k] ?? "");
                        const changed = a !== b;
                        return (
                          <React.Fragment key={k}>
                            <div className="field-name">{k}</div>
                            <div className={changed ? "changed" : ""}>{a || "—"}</div>
                            <div className={changed ? "changed" : ""}>{b || "—"}</div>
                          </React.Fragment>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
