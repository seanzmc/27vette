import React, { useCallback, useEffect, useState } from "react";
import {
  Database, History, ListOrdered, Settings2, GitBranch,
} from "lucide-react";
import { api } from "./api.js";
import FormStructure from "./components/FormStructure.jsx";
import ModelOperations from "./components/ModelOperations.jsx";
import ChangesSync from "./components/ChangesSync.jsx";
import HistoryView from "./components/HistoryView.jsx";

const DRAFT_STORAGE_KEY = "27vette-workbook-manager-draft";
const TERMINAL_DRAFT_STATES = new Set([
  "applied", "cancelled", "manually_resolved_restored",
  "manually_resolved_applied", "abandoned_unknown",
]);

function newDraftId() {
  return `manager-${crypto.randomUUID()}`;
}

export default function App() {
  const [tab, setTab] = useState("structure");
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [modelKey, setModelKey] = useState("stingray");
  const [fatal, setFatal] = useState("");
  const [draftId, setDraftId] = useState("");
  const [draftLifecycle, setDraftLifecycle] = useState(null);

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

  const refreshDraft = useCallback(async (id = draftId) => {
    if (!id) return null;
    try {
      const lifecycle = await api.draftLifecycle(id);
      setDraftLifecycle(lifecycle);
      return lifecycle;
    } catch (e) {
      if (e.status === 404) {
        setDraftLifecycle(null);
        return null;
      }
      throw e;
    }
  }, [draftId]);

  const selectDraft = useCallback((id) => {
    localStorage.setItem(DRAFT_STORAGE_KEY, id);
    setDraftId(id);
    setDraftLifecycle(null);
  }, []);

  const startNewDraft = useCallback(() => {
    selectDraft(newDraftId());
    setTab("operations");
  }, [selectDraft]);

  const refreshManager = useCallback(async ({ draft = true } = {}) => {
    await Promise.all([
      refreshStatus(),
      draft ? refreshDraft() : Promise.resolve(null),
    ]);
  }, [refreshStatus, refreshDraft]);

  useEffect(() => {
    refreshStatus();
    (async () => {
      try {
        const listed = await api.drafts();
        const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
        const savedRow = listed.drafts.find((draft) => draft.id === saved);
        const resumable = listed.drafts.find(
          (draft) => !TERMINAL_DRAFT_STATES.has(draft.status)
        );
        const recoveredId = savedRow && !TERMINAL_DRAFT_STATES.has(savedRow.status)
          ? savedRow.id
          : resumable?.id;
        selectDraft(recoveredId || newDraftId());
        if (recoveredId) await refreshDraft(recoveredId);
      } catch (e) {
        setFatal(`Draft recovery failed: ${e.message}`);
      }
    })();
  }, []); // eslint-disable-line

  const operationCount = draftLifecycle?.operations?.length ?? 0;
  const draftMutable = !draftLifecycle || draftLifecycle.draft.status === "draft";

  const tabs = [
    { id: "structure", label: "Form Structure", icon: ListOrdered },
    { id: "operations", label: "Model Operations", icon: Settings2 },
    {
      id: "changes",
      label: "Draft Review",
      icon: GitBranch,
      badge: operationCount || null,
    },
    { id: "history", label: "History", icon: History },
  ];

  return (
    <div>
      <div className="provisional-banner" role="status">
        <div>
          <strong>Durable draft mode</strong>
          <span>Workbook apply is unavailable; edits remain in reviewed manager state.</span>
        </div>
        <div className="status-surfaces" aria-label="Workbook Manager states">
          <span className="chip">projection: {status?.projection?.state || "loading"}</span>
          <span className="chip">draft: {status?.draft?.state || "loading"}</span>
          <span className="chip">workbook: {status?.workbook?.state || "loading"}</span>
          <span className="chip">generated artifacts: {status?.generated_artifacts?.state || "loading"}</span>
          <span className="chip">publication: {status?.publication?.state || "loading"}</span>
        </div>
      </div>
      <header className="app-header">
        <div className="app-title">
          <Database size={20} color="var(--accent)" />
          <div>
            <h1>27vette Workbook Manager</h1>
            <div className="sub">
              {status?.workbook?.workbook_path?.split("/").pop() || "…"}
              {status?.workbook?.stale && (
                <span className="chip warn" style={{ marginLeft: 8 }}>
                  workbook changed on disk — verified re-import required
                </span>
              )}
              {status?.workbook?.excel_lock && (
                <span className="chip err" style={{ marginLeft: 8 }}>
                  Excel lock present
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
            draftId={draftId}
            draftMutable={draftMutable}
            onChanged={refreshManager}
          />
        )}
        {tab === "operations" && (
          <ModelOperations
            models={models}
            modelKey={modelKey}
            setModelKey={setModelKey}
            draftId={draftId}
            draftMutable={draftMutable}
            onChanged={refreshManager}
          />
        )}
        {tab === "changes" && (
          <ChangesSync
            status={status}
            draftId={draftId}
            lifecycle={draftLifecycle}
            onChanged={refreshManager}
            onStartNew={startNewDraft}
          />
        )}
        {tab === "history" && <HistoryView models={models} />}
      </main>
    </div>
  );
}
