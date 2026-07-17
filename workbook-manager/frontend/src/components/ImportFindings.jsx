import React, { useMemo } from "react";
import { ShieldAlert } from "lucide-react";

import {
  blockingFindings,
  findingViewModel,
} from "../tableRegistry.js";

export default function ImportFindings({
  findings = [], importRunId = null, status = "ready", error = "", onRetry,
}) {
  const rows = useMemo(
    () => findings.map(findingViewModel),
    [findings]
  );
  const blockers = blockingFindings(rows);

  return (
    <div>
      <div className="section-heading">
        <ShieldAlert size={14} /> Import &amp; Contract Findings
      </div>

      {status === "loading" && (
        <div className="panel">
          <div className="empty" role="status">Loading import findings…</div>
        </div>
      )}

      {status === "error" && (
        <div className="notice err" role="alert">
          <strong>Unable to load import findings.</strong>{" "}
          {error || "The findings request failed."}
          {onRetry && (
            <button className="btn small" style={{ marginLeft: 10 }} onClick={onRetry}>Retry</button>
          )}
        </div>
      )}

      {status === "ready" && blockers.length > 0 && (
        <div className="notice err" role="alert">
          <strong>{blockers.length} blocking finding(s).</strong>{" "}
          Resolve contract mismatches before promotion. A business decision is
          required wherever the status is <span className="mono">decision_required</span>;
          no automatic fix is available.
        </div>
      )}

      {status === "ready" && (
      <div className="panel" style={{ marginTop: 10 }}>
        <div className="panel-head">
          <span className="muted">
            Evidence reported by the canonical workbook import and runtime
            contract audit.
          </span>
          <div className="toolbar">
            {importRunId != null && (
              <span className="chip mono">Import run · {importRunId}</span>
            )}
            <span className={`chip ${blockers.length ? "err" : "on"}`}>
              {blockers.length ? `${blockers.length} blocking` : "No blockers"}
            </span>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="empty">
            No import or contract findings are recorded for the current run.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Source trace</th>
                  <th>Code</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((finding, index) => (
                  <tr key={`${finding.code}-${finding.sourceLabel}-${index}`}>
                    <td>
                      <span className={`chip ${finding.severity === "error" ? "err" : "warn"}`}>
                        {finding.severity || "unknown"}
                      </span>
                    </td>
                    <td>
                      <span className={`chip ${finding.blocking ? "err" : ""}`}>
                        {finding.status || "unknown"}
                      </span>
                      {finding.status === "decision_required" && (
                        <div className="faint" style={{ marginTop: 4, fontSize: 11 }}>
                          Blocking · business decision required
                        </div>
                      )}
                    </td>
                    <td>
                      {finding.model_key
                        ? <span className="chip blue">{finding.model_key}</span>
                        : <span className="faint">All models</span>}
                    </td>
                    <td>
                      <div className="toolbar" aria-label={finding.sourceLabel}>
                        <span className="chip mono">
                          {finding.source_sheet || "unknown sheet"}
                        </span>
                        {finding.source_row != null && (
                          <span className="chip mono">row {finding.source_row}</span>
                        )}
                        {finding.source_column && (
                          <span className="chip mono">{finding.source_column}</span>
                        )}
                      </div>
                    </td>
                    <td className="mono">{finding.code || "—"}</td>
                    <td style={{ whiteSpace: "normal", minWidth: 260 }}>
                      {finding.message || "No message supplied."}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}
    </div>
  );
}
