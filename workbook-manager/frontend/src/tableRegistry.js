import { humanize } from "./naming.js";

const BLOCKING_FINDING_STATUSES = new Set([
  "contract_mismatch",
  "decision_required",
]);

/** Build display data exclusively from the server's registry response. */
export function tableViewModel(table) {
  const sourceSheets = Array.isArray(table.source_sheets)
    ? table.source_sheets
    : [];
  return {
    ...table,
    key: table.role,
    label: humanize(table.role),
    sqlTable: table.sql_table,
    sourceSheets,
    sourceLabel: sourceSheets.join(" · ") || "No source sheet recorded",
  };
}

export function blockingFindings(findings) {
  return findings.filter((finding) =>
    BLOCKING_FINDING_STATUSES.has(finding.status)
  );
}

export function findingViewModel(finding) {
  const parts = [];
  if (finding.source_sheet) parts.push(finding.source_sheet);
  if (finding.source_row != null) parts.push(`row ${finding.source_row}`);
  if (finding.source_column) parts.push(finding.source_column);
  const blocking = BLOCKING_FINDING_STATUSES.has(finding.status);
  return {
    ...finding,
    blocking,
    canAutoFix: false,
    sourceLabel: parts.join(" · ") || "No source location recorded",
  };
}

export function importReportViewModel(report) {
  const findings = Array.isArray(report.findings) ? report.findings : [];
  return {
    status: report.status,
    findings,
    findingCount: findings.length,
    blockingCount: blockingFindings(findings).length,
  };
}

export function fieldInputValue(column, value) {
  if (column.ctype === "bool" && value !== "" && value != null) {
    return value === true || value === 1 || value === "1" || value === "True"
      ? "True"
      : "False";
  }
  return value ?? "";
}
