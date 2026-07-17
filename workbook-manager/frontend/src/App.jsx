import React, { useCallback, useEffect, useState } from "react";
import {
  Database, History, ListOrdered, Settings2, GitBranch, ShieldAlert,
} from "lucide-react";
import { api } from "./api.js";
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
  const [findings, setFindings] = useState([]);
  const [importRunId, setImportRunId] = useState(null);
  const [fatal, setFatal] = useState("");

  const refreshStatus = useCallback(async () => {
    try {
      let currentStatus = await api.status();
      setStatus(currentStatus);
      let importBlocked = false;
      if (!currentStatus.last_import) {
        const report = await api.runImport().catch((e) => {
          const blocked = e.detail?.findings || [];
          setFindings(blocked);
          setImportRunId(null);
          setFatal(`Initial import blocked: ${e.message}`);
          importBlocked = true;
          return null;
        });
        if (report) {
          setFindings(report.findings || []);
          currentStatus = await api.status();
          setStatus(currentStatus);
        }
      }
      const latestRunId = currentStatus.last_import?.id;
      if (latestRunId != null) {
        const report = await api.findings(latestRunId);
        setFindings(report.findings);
        setImportRunId(latestRunId);
      }
      const m = await api.models();
      setModels(m.models);
      if (m.models.length && !m.models.some((x) => x.model_key === modelKey)) {
        setModelKey(m.models[0].model_key);
      }
      if (!importBlocked) setFatal("");
    } catch (e) {
      setFatal(`Backend unreachable: ${e.message}`);
    }
  }, [modelKey]);

  useEffect(() => { refreshStatus(); }, []); // eslint-disable-line

  useEffect(() => {
    const showBlockedImport = (event) => {
      setFindings(event.detail?.findings || []);
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
  const blockingCount = blockingFindings(findings).length;

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
          <ImportFindings findings={findings} importRunId={importRunId} />
        )}
        {tab === "changes" && (
          <ChangesSync status={status} onChanged={refreshStatus} />
        )}
        {tab === "history" && <HistoryView models={models} />}
      </main>
    </div>
  );
}
