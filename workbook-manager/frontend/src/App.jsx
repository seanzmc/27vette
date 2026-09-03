import React, { useCallback, useEffect, useState } from "react";
import {
  BookOpen, Database, Images, LayoutPanelTop, Layers3, Search, Settings2, GitBranch,
} from "lucide-react";
import { api } from "./api.js";
import FormStructure from "./components/FormStructure.jsx";
import ModelOperations from "./components/ModelOperations.jsx";
import AssetManager from "./components/AssetManager.jsx";
import ChangesSync, { operatorLifecycle } from "./components/ChangesSync.jsx";
import HistoryView from "./components/HistoryView.jsx";
import ConnectedExplorer from "./components/ConnectedExplorer.jsx";
import SectionsLayout from "./components/SectionsLayout.jsx";
import { parseNavigation, serializeNavigation } from "./navigationState.js";

const DRAFT_STORAGE_KEY = "27vette-workbook-manager-draft";
const TERMINAL_DRAFT_STATES = new Set([
  "applied", "cancelled", "manually_resolved_restored",
  "manually_resolved_applied", "abandoned_unknown",
]);

function newDraftId() {
  return `manager-${crypto.randomUUID()}`;
}

export default function App() {
  const [navigation, setNavigation] = useState(
    () => parseNavigation(window.location.search)
  );
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [fatal, setFatal] = useState("");
  const [draftId, setDraftId] = useState("");
  const [draftLifecycle, setDraftLifecycle] = useState(null);
  const [startup, setStartup] = useState("Starting Workbook Manager");
  const tab = navigation.workspace;
  const modelKey = navigation.model;

  const commitNavigation = useCallback((next, { replace = false, state = {} } = {}) => {
    if (replace) {
      window.history.replaceState(state, "", serializeNavigation(next));
    } else {
      window.history.pushState(state, "", serializeNavigation(next));
    }
    setNavigation(next);
  }, []);

  const setTab = useCallback((workspace) => {
    const model = navigation.model === "*" && workspace !== "assets"
      ? models[0]?.model_key || ""
      : navigation.model;
    commitNavigation({ ...navigation, model, workspace, type: "", id: "" });
  }, [commitNavigation, models, navigation]);

  const setModelKey = useCallback((model) => {
    commitNavigation({ ...navigation, model });
  }, [commitNavigation, navigation]);

  const refreshStatus = useCallback(async () => {
    try {
      setStartup("Loading and checking workbook data");
      const s = await api.status();
      setStatus(s);
      const projectionReady = s.projection?.state === "current";
      const modelResponse = projectionReady ? await api.models() : { models: [] };
      setModels(modelResponse.models);
      if (
        modelResponse.models.length &&
        !(modelKey === "*" && tab === "assets") &&
        !modelResponse.models.some((model) => model.model_key === modelKey)
      ) {
        setModelKey(modelResponse.models[0].model_key);
      }
      if (projectionReady) {
        setStartup(s.draft?.unresolved_total ? "Draft requires attention" : "Ready to edit");
      } else if (s.workbook?.state === "stale") {
        setStartup("Workbook changed—reload latest data");
      } else if (s.projection?.reimport_allowed) {
        setStartup("Loading and checking workbook data");
      } else {
        setStartup("Workbook recovery required");
      }
      setFatal("");
    } catch (e) {
      setStartup("Cannot reach Manager backend");
      setFatal(`Backend unreachable: ${e.message}`);
    }
  }, [modelKey, tab]);

  const refreshDraft = useCallback(async (id = draftId) => {
    if (!id) return null;
    try {
      // Fetch the exact lifecycle directly: history records can point at
      // drafts beyond the bounded /api/drafts list window, and a new draft id
      // has no list row at all. A 404 clears the stale lifecycle view.
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
    setTab("options");
  }, [selectDraft, setTab]);

  const refreshManager = useCallback(async ({ draft = true } = {}) => {
    await Promise.all([
      refreshStatus(),
      draft ? refreshDraft() : Promise.resolve(null),
    ]);
  }, [refreshStatus, refreshDraft]);

  // Contextual editors must keep their post-Save overlay mounted. Refreshing
  // global status temporarily marks the app unready and unmounts the active
  // workspace, so these editors refresh only the durable draft evidence.
  const refreshDraftInPlace = useCallback(
    () => refreshDraft(),
    [refreshDraft],
  );

  useEffect(() => {
    window.history.replaceState(
      window.history.state || {}, "", serializeNavigation(navigation)
    );
    const restoreNavigation = () => {
      setNavigation(parseNavigation(window.location.search));
    };
    window.addEventListener("popstate", restoreNavigation);
    return () => window.removeEventListener("popstate", restoreNavigation);
  }, []); // eslint-disable-line

  useEffect(() => {
    refreshStatus();
    (async () => {
      try {
        const listed = await api.drafts();
        const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
        const savedRow = listed.drafts.find((draft) => draft.id === saved);
        const savedTerminalReview = savedRow
          && TERMINAL_DRAFT_STATES.has(savedRow.status)
          && parseNavigation(window.location.search).workspace === "changes";
        const resumable = listed.drafts.find(
          (draft) => !TERMINAL_DRAFT_STATES.has(draft.status)
        );
        const recoveredId = savedRow && (
          !TERMINAL_DRAFT_STATES.has(savedRow.status) || savedTerminalReview
        )
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
  const draftRevision = draftLifecycle?.draft?.updated_ts || "";
  const draftMutable = !draftLifecycle || draftLifecycle.draft.status === "draft";
  const ready = startup === "Ready to edit" || startup === "Draft requires attention";
  // Apply intentionally makes the projection stale. Keep Review & Apply
  // mounted so the operator can read the durable completion/recovery evidence
  // before choosing the separately guarded workbook reload.
  const reviewAvailable = tab === "changes" && Boolean(draftLifecycle);

  const tabs = [
    { id: "overview", label: "Form Overview", icon: BookOpen },
    { id: "sections", label: "Sections & Layout", icon: LayoutPanelTop },
    { id: "options", label: "Options & Relationships", icon: Search },
    { id: "groups", label: "Groups", icon: Layers3 },
    { id: "assets", label: "Images", icon: Images },
    {
      id: "changes",
      label: "Review & Apply",
      icon: GitBranch,
      badge: operationCount || null,
    },
    { id: "advanced", label: "Advanced & Recovery", icon: Settings2 },
  ];

  const reloadWorkbook = async () => {
    try {
      setStartup("Loading and checking workbook data");
      setFatal("");
      await api.runImport();
      await refreshStatus();
    } catch (e) {
      setStartup("Workbook recovery required");
      setFatal(`Reload failed: ${e.message}`);
    }
  };

  return (
    <div>
      <div className="readiness-banner" role="status">
        <div>
          <strong>{startup}</strong>
          <span>{ready
            ? "Connected views are current. Guarded workbook workflow keeps draft saves provisional."
            : "Normal workspaces wait for verified workbook data."}</span>
        </div>
        <span className="chip">{operationCount} draft change{operationCount === 1 ? "" : "s"}</span>
        {!ready && status?.projection?.reimport_allowed && (
          <button className="btn primary small" onClick={reloadWorkbook}>
            Reload Latest Workbook Data
          </button>
        )}
      </div>
      <details className="system-details">
        <summary>System details</summary>
        <div className="status-surfaces" aria-label="Workbook Manager states">
          <span className="chip">projection: {status?.projection?.state || "loading"}</span>
          <span className="chip">draft: {status?.draft?.state || "loading"}</span>
          <span className="chip">workbook: {status?.workbook?.state || "loading"}</span>
          <span className="chip">generated artifacts: {status?.generated_artifacts?.state || "loading"}</span>
          <span className="chip">publication: {status?.publication?.state || "loading"}</span>
        </div>
      </details>
      <header className="app-header">
        <div className="app-title">
          <Database size={20} color="var(--accent)" />
          <div>
            <h1>27vette Workbook Manager</h1>
            <div className="sub">
              {status?.workbook?.workbook_path?.split("/").pop() || "…"}
              {status?.workbook?.excel_lock && (
                <span className="chip err" style={{ marginLeft: 8 }}>Excel lock present</span>
              )}
            </div>
          </div>
        </div>
        <label className="model-context">
          <span>Model</span>
          <select
            value={modelKey}
            onChange={(e) => setModelKey(e.target.value)}
            disabled={!ready}
          >
            {tab === "assets" && <option value="*">All models</option>}
            {models.map((model) => (
              <option key={model.model_key} value={model.model_key}>
                {model.label || model.model_key}
              </option>
            ))}
          </select>
        </label>
        <button
          className="draft-tray"
          onClick={() => setTab("changes")}
          disabled={!ready && !draftLifecycle}
        >
          <strong>{draftLifecycle?.draft?.id || draftId || "Preparing draft"}</strong>
          <span>
            {operatorLifecycle[draftLifecycle?.draft?.status] || "Collecting draft changes"} · {operationCount} change{operationCount === 1 ? "" : "s"}
          </span>
        </button>
        <nav className="tabs" aria-label="Workbook Manager workspaces">
          {tabs.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
              disabled={!ready && !["changes", "advanced"].includes(id)}
            >
              <Icon size={14} /> {label}
              {badge ? <span className="badge">{badge}</span> : null}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {fatal && (
          <div className="notice err">
            {fatal}<div className="muted">The canonical workbook was not changed.</div>
          </div>
        )}
        {!ready && !reviewAvailable && (
          <section className="startup-state">
            <Database size={34} />
            <h2>{startup}</h2>
            <p>Workbook data must be verified before connected options, groups, images, or draft actions can load.</p>
            {status?.projection?.reimport_allowed && (
              <button className="btn primary" onClick={reloadWorkbook}>
                Reload Latest Workbook Data
              </button>
            )}
          </section>
        )}
        {ready && tab === "overview" && (
          <FormStructure
            models={models}
            modelKey={modelKey}
            setModelKey={setModelKey}
            draftId={draftId}
            draftRevision={draftRevision}
            draftMutable={draftMutable}
            onChanged={refreshManager}
          />
        )}
        {ready && tab === "sections" && (
          <SectionsLayout
            modelKey={modelKey}
            navigation={navigation}
            onNavigationChange={commitNavigation}
            draftId={draftId}
            draftRevision={draftRevision}
            draftMutable={draftMutable}
            onChanged={refreshDraftInPlace}
          />
        )}
        {ready && (tab === "options" || tab === "groups") && (
          <ConnectedExplorer
            mode={tab}
            modelKey={modelKey}
            navigation={navigation}
            onNavigationChange={commitNavigation}
            draftId={draftId}
            draftRevision={draftRevision}
            draftMutable={draftMutable}
            onChanged={refreshDraftInPlace}
          />
        )}
        {ready && tab === "assets" && (
          <AssetManager
            modelKey={modelKey}
            setModelKey={setModelKey}
            navigation={navigation}
            onNavigationChange={commitNavigation}
            draftId={draftId}
            draftMutable={draftMutable}
            draftLifecycle={draftLifecycle}
            onChanged={refreshManager}
          />
        )}
        {(ready || reviewAvailable) && tab === "changes" && (
          <ChangesSync
            status={status}
            draftId={draftId}
            lifecycle={draftLifecycle}
            onChanged={refreshManager}
            onStartNew={startNewDraft}
            onSelectDraft={async (id) => {
              selectDraft(id);
              await refreshDraft(id);
              setTab("changes");
            }}
          />
        )}
        {(ready || status) && tab === "advanced" && (
          <div className="advanced-layout">
            <HistoryView
              models={models}
              onOpenDraft={async (id) => {
                selectDraft(id);
                await refreshDraft(id);
                setTab("changes");
              }}
            />
            {ready ? (
              <section>
                <h2>Raw collection browser</h2>
                <p className="muted">Workbook-shaped tables remain available for advanced traceability and maintenance.</p>
                <ModelOperations
                  models={models}
                  modelKey={modelKey}
                  setModelKey={setModelKey}
                  draftId={draftId}
                  draftMutable={draftMutable}
                  navigation={navigation}
                  onNavigationChange={commitNavigation}
                  onChanged={refreshDraftInPlace}
                />
              </section>
            ) : (
              <div className="notice warn">
                Raw collection browsing requires a current verified projection. Durable Workflow history remains available.
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
