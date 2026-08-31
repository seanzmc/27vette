function messageText(item) {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") {
    if (item.id && item.message) return `${item.id}: ${item.message}`;
    return item.message || JSON.stringify(item);
  }
  return String(item ?? "");
}

function attemptMessages(attempt) {
  if (!attempt) return [];
  const result = attempt.result || {};
  const errors = (result.errors || []).map(messageText);
  if (attempt.exception_message) {
    errors.unshift(`${attempt.exception_class || "Error"}: ${attempt.exception_message}`);
  }
  return errors.filter(Boolean);
}

// Rollback errors are already copied into the attempt's top-level
// result.errors by complete_apply_rebuild(). Presenting the same evidence twice
// obscures it, so combined message lists keep the first occurrence only.
function dedupeMessages(messages) {
  const seen = new Set();
  return messages.filter((message) => {
    if (seen.has(message)) return false;
    seen.add(message);
    return true;
  });
}

const MANUAL_RESOLUTION_STATES = new Set([
  "manually_resolved_restored",
  "manually_resolved_applied",
  "abandoned_unknown",
]);

function outputRollbackState(rebuild) {
  const generated = rebuild?.generated_contracts?.state || "unknown";
  const publication = rebuild?.publication?.state || "unknown";
  return generated === publication
    ? generated
    : `generated contracts ${generated}; publication ${publication}`;
}

function applyFailureSummary(applyAttempt, manualResolution) {
  if (!applyAttempt || applyAttempt.manager_state === "applied") return null;
  // A recorded manual resolution supersedes the immutable failed attempt: the
  // recovery verb is no longer available, so never keep advertising it.
  const resolvedState = MANUAL_RESOLUTION_STATES.has(manualResolution?.manager_state)
    ? manualResolution.manager_state
    : null;
  const result = applyAttempt.result || {};
  const rebuild = result.applyRebuild || null;
  const rollback = rebuild?.rollback || {};
  const errors = dedupeMessages([
    ...attemptMessages(applyAttempt),
    ...(rollback.errors || []).map(messageText),
  ].filter(Boolean));
  const allowed = new Set(applyAttempt.allowed_verbs || []);
  const restorationIsSafe = applyAttempt.manager_state === "apply_restored_retryable"
    ? rebuild?.workbook?.state === "restored"
      && rollback.state === "verified"
      && rollback.verified === true
    : applyAttempt.manager_state !== "workbook_state_unknown";
  const safeToRetryOrCancel = !resolvedState
    && restorationIsSafe
    && (allowed.has("retry_apply") || allowed.has("cancel"));
  const nextAction = resolvedState
    ? `none; manual recovery recorded (${resolvedState.replaceAll("_", " ")})`
    : safeToRetryOrCancel
    ? [
        allowed.has("retry_apply") ? "retry apply" : "",
        allowed.has("cancel") ? "cancel" : "",
      ].filter(Boolean).join(" or ")
    : "manual recovery";

  return {
    failed_stage: rebuild ? "form data rebuild or publication" : "workbook apply",
    error: errors[0] || "Apply and Rebuild did not finish cleanly.",
    workbook_rollback: rebuild?.workbook?.state || result.workbookState || "unknown",
    output_rollback: rebuild ? outputRollbackState(rebuild) : "not started",
    safe_to_retry_or_cancel: safeToRetryOrCancel,
    next_action: nextAction,
  };
}

export function lifecyclePresentation({
  previewAttempt = null,
  approvalAttempt = null,
  applyAttempt = null,
  manualResolution = null,
} = {}) {
  const preview = previewAttempt?.result || {};
  const warnings = (preview.warnings || []).map(messageText).filter(Boolean);
  const rollbackErrors = (
    applyAttempt?.result?.applyRebuild?.rollback?.errors || []
  ).map(messageText).filter(Boolean);
  const manualMessages = manualResolution
    ? [
        manualResolution.evidence?.note
          || `Manual recovery recorded: ${manualResolution.manager_state || "resolved"}`,
      ]
    : [];
  const messages = dedupeMessages([
    ...warnings,
    ...attemptMessages(previewAttempt),
    ...attemptMessages(approvalAttempt),
    ...attemptMessages(applyAttempt),
    ...rollbackErrors,
    ...manualMessages,
  ]);

  return {
    empty: messages.length === 0,
    messages,
    apply_summary: applyFailureSummary(applyAttempt, manualResolution),
  };
}
