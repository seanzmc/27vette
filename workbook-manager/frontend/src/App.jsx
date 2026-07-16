import React, { useCallback, useEffect, useState } from "react";
import {
  Database, History, ListOrdered, Settings2, GitBranch,
} from "lucide-react";
import { api } from "./api.js";
import FormStructure from "./components/FormStructure.jsx";
import ModelOperations from "./components/ModelOperations.jsx";
import ChangesSync from "./components/ChangesSync.jsx";
import HistoryView from "./components/HistoryView.jsx";

export default function App() {
  const [tab, setTab] = useState("structure");
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [modelKey, setModelKey] = useState("stingray");
  const [fatal, setFatal] = useState("");

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.status();
      setStatus(s);
      if (!s.last_import) {
        const report = await api.runImport().catch((e) => {
          setFatal(`Initial import failed: ${e.message}`);
          return null;
        });
        if (report) setStatus(await api.status());
      }
      const m = await api.models();
      setModels(m.models);
      if (m.models.length && !m.models.some((x) => x.model_key === modelKey)) {
        setModelKey(m.models[0].model_key);
      }
      setFatal("");
    } catch (e) {
      setFatal(`Backend unreachable: ${e.message}`);
    }
  }, [modelKey]);

  useEffect(() => { refreshStatus(); }, []); // eslint-disable-line

  const staged = status?.staged_changes ?? 0;
  const unsynced = status?.unsynced_committed_changes ?? 0;

  const tabs = [
    { id: "structure", label: "Form Structure", icon: ListOrdered },
    { id: "operations", label: "Model Operations", icon: Settings2 },
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
        {tab === "changes" && (
          <ChangesSync status={status} onChanged={refreshStatus} />
        )}
        {tab === "history" && <HistoryView models={models} />}
      </main>
    </div>
  );
}
