import React from "react";
import {
  changedFieldEntries,
  hasDraftOverlay,
  operationLabel,
  overlayBlockReason,
  overlayStateLabel,
} from "../draftOverlayModel.js";

// Checkpoint 2C: the one draft-overlay panel every connected detail renders.
// It reads the backend adapter's shape verbatim — state, exact operation,
// changed fields with explicit before/after, direct impact, and conflicts — so
// option, group, section, structure, and asset surfaces present proposed values
// identically and none patches its heading independently.

function cell(value) {
  return value === null || value === undefined
    ? <em>SQL NULL</em>
    : String(value);
}

export function EffectiveText({
  overlay, field, authored, className = "", format = (value) => value,
}) {
  const pair = overlay?.changed_fields?.[field];
  const active = overlay?.state === "modified" || overlay?.state === "added";
  if (!pair || !active) return <span className={className}>{format(authored)}</span>;
  const proposed = pair.after === null || pair.after === undefined ? cell(pair.after) : format(pair.after);
  // An added row has no authored value to strike through; it is proposed-only.
  if (overlay.state === "added") {
    return <span className={`effective-text ${className}`} data-field={field}><span className="proposed-value">{proposed}</span></span>;
  }
  // The struck-through side is the authored value. Structure nodes arrive
  // already mutated to their effective value, so the caller's `authored` prop
  // can itself be the proposed value; when it provably mirrors `pair.after`,
  // fall back to the backend-owned `pair.before`. Otherwise the prop keeps its
  // own display semantics (derived labels like Yes/No or factual fallbacks).
  const authoredValue = String(authored) === String(pair.after)
    ? pair.before === null || pair.before === undefined
      ? cell(pair.before)
      : format(pair.before)
    : format(authored);
  return (
    <span className={`effective-text ${className}`} data-field={field}>
      <s className="authored-value">{authoredValue}</s>
      <span className="proposed-value">{proposed}</span>
    </span>
  );
}

export default function DraftOverlay({
  overlay, impactLabels = {}, emptyMessage = "", testId = "draft-overlay",
}) {
  if (!hasDraftOverlay(overlay)) {
    return emptyMessage
      ? <p className="muted" data-testid={testId}>{emptyMessage}</p>
      : null;
  }
  const changed = changedFieldEntries(overlay);
  const blockReason = overlayBlockReason(overlay);
  const impact = Object.entries(overlay.direct_impact || {});
  return (
    <div
      className={`panel draft-overlay ${overlay.state}`}
      role={overlay.state === "conflicted" ? "alert" : "status"}
      data-testid={testId}
      data-state={overlay.state}
    >
      <div className="draft-overlay-head">
        <strong>{overlayStateLabel(overlay)}</strong>
        <span className="mono faint">{operationLabel(overlay)}</span>
      </div>
      {overlay.state === "conflicted" && (
        <p className="draft-overlay-reason">
          {blockReason} The authored values below remain in effect; editing is blocked until the draft is rebound or replaced.
        </p>
      )}
      {overlay.state === "pending_deletion" && (
        <p className="draft-overlay-reason">
          This row is proposed for deletion. The authored values stay visible here and remain in the workbook until Write Approved Changes &amp; Rebuild Form Data.
        </p>
      )}
      {overlay.state === "added" && (
        <p className="draft-overlay-reason">
          This row exists only in the draft; there is no authored value yet.
        </p>
      )}
      {changed.length > 0 && overlay.state !== "pending_deletion" && (
        <div className="field-diff" aria-label="Authored and proposed values">
          <div className="field-name">Field</div>
          <div className="before-value">Authored</div>
          <div className="after-value">Proposed</div>
          {changed.map(({ field, before, after }) => (
            <React.Fragment key={field}>
              <div className="field-name">{field}</div>
              <div className="before-value">{cell(before)}</div>
              <div className="after-value">{cell(after)}</div>
            </React.Fragment>
          ))}
        </div>
      )}
      {impact.length > 0 && (
        <>
          <h3>Direct impact</h3>
          <div className="detail-facts">
            {impact.map(([key, count]) => (
              <span key={key}><strong>{impactLabels[key] || key.replaceAll("_", " ")}</strong>{count}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
