import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Database, History, ListOrdered, Settings2, GitBranch, ShieldAlert,
} from "lucide-react";
import { api } from "./api.js";
import { isCurrentGeneration } from "./requestGuards.js";
import { blockingFindings } from "./tableRegistry.js";
import FormStructure from "./components/FormStructure.jsx";
import ModelOperations from "./components/ModelOperations.jsx";
import ChangesSync from "./components/ChangesSync.jsx";
import HistoryView from "./components/HistoryView.jsx";
import ImportFindings from "./components/ImportFindings.jsx";

export default function App() {
  const [tab, setTab] = useState("structure");
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [modelKey, setModelKey] = useState("stingray");
  const [findingState, setFindingState] = useState({
    status: "loading",
    items: [],
    error: "",
  });
  const [importRunId, setImportRunId] = useState(null);
  const [fatal, setFatal] = useState("");
  const statusGenerationRef = useRef(0);

  const refreshStatus = useCallback(async (completedImport = null) => {
    const requestGeneration = ++statusGenerationRef.current;
    const isCurrent = () => isCurrentGeneration(
      requestGeneration,
      statusGenerationRef.current,
    );
    const importReport = Array.isArray(completedImport?.findings)
      ? completedImport
      : null;
    setFindingState((current) => importReport
      ? {
        status: "ready",
        items: importReport.findings,
        error: "",
      }
      : {
        status: "loading",
        items: current.items,
        error: "",
      });
    if (importReport) setImportRunId(null);
    try {
      let currentStatus = await api.status();
      if (!isCurrent()) return;
      setStatus(currentStatus);
      let importBlocked = false;
      if (!currentStatus.last_import) {
        let report = null;
        try {
          report = await api.runImport();
        } catch (e) {
          if (!isCurrent()) return;
          const blocked = e.detail?.findings || [];
          setFindingState({ status: "ready", items: blocked, error: "" });
          setImportRunId(null);
          setFatal(`Initial import blocked: ${e.message}`);
          importBlocked = true;
        }
        if (report) {
          if (!isCurrent()) return;
          setFindingState({
            status: "ready",
            items: report.findings || [],
            error: "",
          });
          currentStatus = await api.status();
          if (!isCurrent()) return;
          setStatus(currentStatus);
        }
      }
      const latestRunId = currentStatus.last_import?.id;
      if (latestRunId != null) {
        if (!isCurrent()) return;
        setFindingState((current) => ({
          status: "loading",
          items: current.items,
          error: "",
        }));
        try {
          const report = await api.findings(latestRunId);
          if (!isCurrent()) return;
          setFindingState({
            status: "ready",
            items: report.findings,
            error: "",
          });
          setImportRunId(latestRunId);
        } catch (error) {
          if (!isCurrent()) return;
          setFindingState((current) => ({
            status: "error",
            items: current.items,
            error: error.message,
          }));
        }
      } else if (!importBlocked) {
        if (!isCurrent()) return;
        setFindingState((current) => ({
          status: "ready",
          items: current.items,
          error: "",
        }));
      }
      if (importBlocked) return;
      const m = await api.models();
      if (!isCurrent()) return;
      setModels(m.models);
      if (m.models.length && !m.models.some((x) => x.model_key === modelKey)) {
        setModelKey(m.models[0].model_key);
      }
      if (!importBlocked) setFatal("");
    } catch (e) {
      if (!isCurrent()) return;
      setFindingState((current) => ({
        status: "error",
        items: current.items,
        error: e.message,
      }));
      setFatal(`Backend unreachable: ${e.message}`);
    }
  }, [modelKey]);

  useEffect(() => {
    refreshStatus();
    return () => { ++statusGenerationRef.current; };
  }, []); // eslint-disable-line

  useEffect(() => {
    const showBlockedImport = (event) => {
      ++statusGenerationRef.current;
      setFindingState({
        status: "ready",
        items: event.detail?.findings || [],
        error: "",
      });
      setImportRunId(null);
      setTab("findings");
    };
    window.addEventListener("wbm:import-findings", showBlockedImport);
    return () => window.removeEventListener(
      "wbm:import-findings", showBlockedImport
    );
  }, []);

  const staged = status?.staged_changes ?? 0;
  const unsynced = status?.unsynced_committed_changes ?? 0;
  const blockingCount = blockingFindings(findingState.items).length;

  const tabs = [
    { id: "structure", label: "Form Structure", icon: ListOrdered },
    { id: "operations", label: "Model Operations", icon: Settings2 },
    {
      id: "findings",
      label: "Findings",
      icon: ShieldAlert,
      badge: blockingCount || null,
    },
    {
      id: "changes",
      label: "Changes & Sync",
      icon: GitBranch,
      badge: staged + unsynced || null,
    },
    { id: "history", label: "History", icon: History },
  ];

  return (
    <div>
      <header className="app-header">
        <div className="app-title">
          <Database size={20} color="var(--accent)" />
          <div>
            <h1>27vette Workbook Manager</h1>
            <div className="sub">
              {status?.workbook?.workbook_path?.split("/").pop() || "…"}
              {status?.workbook?.stale && (
                <span className="chip warn" style={{ marginLeft: 8 }}>
                  workbook changed on disk — re-import recommended
                </span>
              )}
              {status?.workbook?.excel_lock && (
                <span className="chip err" style={{ marginLeft: 8 }}>
                  Excel lock present — close Excel before sync
                </span>
              )}
            </div>
          </div>
        </div>
        <nav className="tabs">
          {tabs.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
            >
              <Icon size={14} /> {label}
              {badge ? <span className="badge">{badge}</span> : null}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {fatal && <div className="notice err">{fatal}</div>}
        {tab === "structure" && (
          <FormStructure
            models={models}
            modelKey={modelKey}
            setModelKey={setModelKey}
            onChanged={refreshStatus}
          />
        )}
        {tab === "operations" && (
          <ModelOperations
            models={models}
            modelKey={modelKey}
            setModelKey={setModelKey}
            onChanged={refreshStatus}
          />
        )}
        {tab === "findings" && (
          <ImportFindings
            findings={findingState.items}
            importRunId={importRunId}
            status={findingState.status}
            error={findingState.error}
            onRetry={() => refreshStatus()}
          />
        )}
        {tab === "changes" && (
          <ChangesSync
            status={status}
            onChanged={() => refreshStatus()}
            onImportComplete={(report) => refreshStatus(report)}
          />
        )}
        {tab === "history" && <HistoryView models={models} />}
      </main>
    </div>
  );
}
