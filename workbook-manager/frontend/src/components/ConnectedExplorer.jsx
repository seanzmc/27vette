import React, { useEffect, useRef, useState } from "react";
import { ArrowLeft, ExternalLink, LockKeyhole, Pencil, Search } from "lucide-react";
import { api } from "../api.js";
import { navigationForDestination } from "../navigationState.js";
import GroupEditor from "./GroupEditor.jsx";
import OptionEditor from "./OptionEditor.jsx";

function TechnicalDetails({ data }) {
  if (!data) return null;
  return (
    <details className="technical-details">
      <summary>Technical details</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function DraftOverlay({ overlay }) {
  if (!overlay || overlay.state === "unchanged") return null;
  const changed = Object.keys(overlay.effective || overlay.base || {}).filter(
    (key) => overlay.base?.[key] !== overlay.effective?.[key]
  );
  return (
    <div className={`panel draft-overlay ${overlay.state}`} role="status">
      <strong>Draft {overlay.state.replaceAll("_", " ")}</strong>
      <span>
        {overlay.state === "pending_deletion"
          ? "This record remains in the workbook until Apply and Rebuild."
          : `${changed.length} proposed field change${changed.length === 1 ? "" : "s"}.`}
      </span>
    </div>
  );
}

function EntityLink({ destination, children, onNavigate }) {
  const focusKey = `${destination.entity_type}:${destination.entity_id}`;
  return (
    <button
      className="entity-link"
      data-focus-key={focusKey}
      onClick={() => onNavigate(destination)}
    >
      {children}<ExternalLink size={12} />
    </button>
  );
}

function DiagnosticResults({ result, onNavigate }) {
  if (!result) return null;
  return (
    <div className="panel diagnostic-results">
      <div className="panel-head"><strong>{result.diagnostic.label}</strong><span>{result.results.length} results</span></div>
      <div className="relationship-list">
        {result.results.map((row) => (
          <EntityLink key={`${row.entity_type}:${row.entity_id}`} destination={row.destination} onNavigate={onNavigate}>
            <strong>{row.label}</strong><span>{row.direction || row.distinct_status_count || row.distinct_group_count || "Open connected detail"}</span>
          </EntityLink>
        ))}
        {!result.results.length && <p className="muted">No matching relationships in this model.</p>}
      </div>
    </div>
  );
}

function GroupDetail({
  detail, onNavigate, onBack, onDiagnostic, diagnosticResult,
  draftId, draftMutable, onChanged,
}) {
  const [editing, setEditing] = useState("");
  return (
    <section className="explorer-detail" aria-labelledby="group-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference view · edits save to the durable draft</div>
      <h2 id="group-detail-heading">{detail.label}</h2>
      <DraftOverlay overlay={detail.draft_overlay} />
      <p>{detail.notes || "No explanatory notes are authored for this group."}</p>
      <div className="detail-facts">
        <span><strong>Type</strong>{detail.group_type}</span>
        <span><strong>Behavior</strong>{detail.behavior?.replaceAll("_", " ")}</span>
        <span><strong>Members</strong>{detail.member_count}</span>
      </div>
      <div className="detail-actions">
        <button
          className="btn small"
          disabled={!draftMutable}
          title={draftMutable ? "Edit registered group fields in the durable draft" : "The active draft is locked; start a new draft to edit."}
          onClick={() => setEditing("facts")}
        >
          <Pencil size={14} /> Edit group in draft
        </button>
        <button
          className="btn small"
          disabled={!draftMutable}
          title={draftMutable ? "Add, remove, activate, or reorder members in the durable draft" : "The active draft is locked; start a new draft to edit."}
          onClick={() => setEditing("members")}
        >
          <Pencil size={14} /> Manage members in draft
        </button>
        {!draftMutable && <span className="muted">Draft locked — editing unavailable.</span>}
        <button className="btn small" onClick={() => onDiagnostic("where_used", detail.destination.entity_id)}>
          Where this group is used
        </button>
      </div>
      <h3>Members</h3>
      <div className="relationship-list">
        {detail.members.map((member) => (
          <EntityLink key={member.option_id} onNavigate={onNavigate} destination={{
            workspace: "options", entity_type: "option", entity_id: member.option_id,
          }}>
            <strong>{member.rpo} — {member.option_name}</strong>
            <span>{member.section_name || "Section unavailable"}</span>
          </EntityLink>
        ))}
      </div>
      <DiagnosticResults result={diagnosticResult} onNavigate={onNavigate} />
      <TechnicalDetails data={{ group_id: detail.group_id, ...detail.technical }} />
      {editing && (
        <GroupEditor
          detail={detail}
          mode={editing}
          modelKey={detail.model_key}
          draftId={draftId}
          draftMutable={draftMutable}
          onChanged={onChanged}
          onClose={() => setEditing("")}
        />
      )}
    </section>
  );
}

function OptionDetail({
  detail, onNavigate, onBack, onDiagnostic, diagnosticResult,
  draftId, draftMutable, onChanged,
}) {
  const [editing, setEditing] = useState(false);
  const { option } = detail;
  return (
    <section className="explorer-detail" aria-labelledby="option-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference view · edits save to the durable draft</div>
      <h2 id="option-detail-heading">{option.label}</h2>
      <DraftOverlay overlay={detail.draft_overlay} />
      <p>{option.description || option.detail_raw || "No additional customer copy is authored."}</p>
      <div className="detail-facts">
        <span><strong>Section</strong>{detail.section?.section_name || "Unmapped"}</span>
        <span><strong>Base price</strong>{option.price === null ? "Not specified" : `$${Number(option.price).toLocaleString()}`}</span>
        <span><strong>Selectable</strong>{option.selectable === "True" ? "Yes" : "No"}</span>
        <span><strong>Active</strong>{option.active === "True" ? "Yes" : "No"}</span>
      </div>
      <div className="detail-actions">
        <button
          className="btn small"
          disabled={!draftMutable}
          title={draftMutable ? "Edit this option in the durable draft" : "The active draft is locked; start a new draft to edit."}
          onClick={() => setEditing(true)}
        >
          <Pencil size={14} /> Edit option in draft
        </button>
        {!draftMutable && <span className="muted">Draft locked — editing unavailable.</span>}
        <button className="btn small" onClick={() => onDiagnostic("where_used", option.option_id)}>
          Where this option is used
        </button>
        <button className="btn small" onClick={() => onDiagnostic("option_relationships", option.option_id)}>
          Show option relationships
        </button>
      </div>
      <h3>Availability by variant</h3>
      <div className="availability-grid">
        {detail.availability.map((row) => (
          <div key={row.variant_id}><strong>{row.display_name || row.variant_id}</strong><span>{row.status}</span></div>
        ))}
      </div>
      <h3>Groups</h3>
      <div className="relationship-list">
        {[...detail.exclusive_groups, ...detail.rule_groups].map((group) => (
          <EntityLink key={`${group.group_type}:${group.group_id}`} onNavigate={onNavigate} destination={group.destination}>
            <strong>{group.label}</strong><span>{group.behavior?.replaceAll("_", " ")} · {group.member_count} members</span>
          </EntityLink>
        ))}
        {!detail.exclusive_groups.length && !detail.rule_groups.length && <p className="muted">No connected groups.</p>}
      </div>
      <h3>Rules</h3>
      <div className="relationship-list compact">
        {detail.rules.map((rule) => (
          <div key={rule.rule_id}><strong>{rule.rule_type?.replaceAll("_", " ")}</strong><span>{rule.source_rpo || rule.source_id} → {rule.target_rpo || rule.target_id}</span></div>
        ))}
        {!detail.rules.length && <p className="muted">No incoming or outgoing rules.</p>}
      </div>
      <h3>Pricing, defaults, overrides & images</h3>
      <div className="detail-facts">
        <span><strong>Pricing rules</strong>{detail.pricing.length}</span>
        <span><strong>Default rules</strong>{detail.default_rules.length}</span>
        <span><strong>Variant overrides</strong>{detail.variant_overrides.length}</span>
        <span><strong>Images</strong>{detail.assets.length}</span>
      </div>
      <DiagnosticResults result={diagnosticResult} onNavigate={onNavigate} />
      <TechnicalDetails data={detail.technical} />
      {editing && (
        <OptionEditor
          detail={detail}
          modelKey={detail.model_key}
          draftId={draftId}
          draftMutable={draftMutable}
          onChanged={onChanged}
          onClose={() => setEditing(false)}
        />
      )}
    </section>
  );
}

function SectionDetail({ detail, onNavigate, onBack }) {
  return (
    <section className="explorer-detail" aria-labelledby="section-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference only · workbook section</div>
      <h2 id="section-detail-heading">{detail.label}</h2>
      <p>{detail.options.length} options in this section for the selected model.</p>
      <div className="relationship-list">
        {detail.options.map((option) => (
          <EntityLink key={option.entity_id} destination={option.destination} onNavigate={onNavigate}>
            <strong>{option.label}</strong><span>Open connected option</span>
          </EntityLink>
        ))}
      </div>
      <TechnicalDetails data={detail.technical} />
    </section>
  );
}

function RuleDetail({ detail, onNavigate, onBack }) {
  const source = detail.source_option;
  const target = detail.target_option;
  return (
    <section className="explorer-detail" aria-labelledby="rule-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference only · workbook rule</div>
      <h2 id="rule-detail-heading">{detail.rule.rule_type?.replaceAll("_", " ")}</h2>
      <div className="relationship-list">
        {source && <EntityLink destination={{ workspace: "options", entity_type: "option", entity_id: source.option_id }} onNavigate={onNavigate}><strong>{source.rpo} — {source.option_name}</strong><span>Source option</span></EntityLink>}
        {target && <EntityLink destination={{ workspace: "options", entity_type: "option", entity_id: target.option_id }} onNavigate={onNavigate}><strong>{target.rpo} — {target.option_name}</strong><span>Target option</span></EntityLink>}
      </div>
      <TechnicalDetails data={detail.technical} />
    </section>
  );
}

export default function ConnectedExplorer({
  mode, modelKey, navigation, onNavigationChange,
  draftId, draftRevision, draftMutable, onChanged,
}) {
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [diagnostics, setDiagnostics] = useState([]);
  const [diagnosticResult, setDiagnosticResult] = useState(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const timer = useRef(null);
  const detailRequest = useRef(0);
  const searchRequest = useRef(0);
  const query = navigation.query;

  const navigate = (destination) => {
    const focusKey = `${destination.entity_type}:${destination.entity_id}`;
    window.history.replaceState(
      { ...window.history.state, focusKey }, "", window.location.href
    );
    setDiagnosticResult(null);
    onNavigationChange(navigationForDestination(navigation, destination), {
      state: { returnNavigation: navigation },
    });
  };

  useEffect(() => {
    setDiagnosticResult(null);
    api.explorerDiagnostics(modelKey).then((data) => setDiagnostics(data.diagnostics)).catch((e) => setError(e.message));
  }, [modelKey]);

  useEffect(() => {
    const generation = ++detailRequest.current;
    if (!navigation.type || !navigation.id) {
      setSelected(null);
      setDetailError("");
      return;
    }
    // A previous model's detail must never stay interactive under a new
    // model header, or its edit buttons could stage durable intent against
    // the wrong model while the replacement detail loads.
    setSelected((current) => (current?.model_key === modelKey ? current : null));
    setDetailError("");
    const load = async () => {
      try {
        setDetailError("");
        let detail;
        if (navigation.type === "option") {
          detail = await api.connectedOption(modelKey, navigation.id, draftId);
        } else if (navigation.type === "exclusive_group") {
          detail = await api.connectedGroup(modelKey, "exclusive", navigation.id, draftId);
        } else if (navigation.type === "rule_group") {
          detail = await api.connectedGroup(modelKey, "rule", navigation.id, draftId);
        } else if (navigation.type === "section") {
          detail = await api.connectedSection(modelKey, navigation.id);
        } else if (navigation.type === "rule") {
          detail = await api.connectedRule(modelKey, navigation.id);
        }
        if (generation === detailRequest.current) setSelected(detail || null);
      } catch (e) {
        if (generation !== detailRequest.current) return;
        setSelected(null);
        setDetailError(e.status === 404
          ? "This connected item is not available for the selected model. Return to results."
          : e.message);
      }
    };
    load();
  }, [modelKey, navigation.type, navigation.id, draftId, draftRevision]);

  useEffect(() => {
    clearTimeout(timer.current);
    const generation = ++searchRequest.current;
    if (!query.trim()) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      try {
        const data = await api.explorerSearch(modelKey, query);
        if (generation !== searchRequest.current) return;
        setResults(data.results);
        setError("");
      } catch (e) {
        if (generation === searchRequest.current) setError(e.message);
      }
    }, 180);
    return () => clearTimeout(timer.current);
  }, [modelKey, query]);

  useEffect(() => {
    const focusKey = window.history.state?.focusKey;
    if (navigation.type || !focusKey || !results.length) return;
    requestAnimationFrame(() => {
      const target = [...document.querySelectorAll("[data-focus-key]")].find(
        (node) => node.dataset.focusKey === focusKey
      );
      target?.focus();
    });
  }, [navigation.type, results]);

  const search = (value) => {
    onNavigationChange({ ...navigation, query: value }, { replace: true });
  };

  const runDiagnostic = async (item, entityId = "") => {
    try {
      const data = await api.explorerDiagnostic(modelKey, item.key, { entityId, limit: 100 });
      setDiagnosticResult(data); setError("");
    } catch (e) { setError(e.message); }
  };

  const runEntityDiagnostic = (key, entityId) => runDiagnostic({ key }, entityId);

  const backToResults = () => {
    const previous = window.history.state?.returnNavigation;
    if (previous) {
      window.history.back();
    } else {
      onNavigationChange({ ...navigation, type: "", id: "" });
    }
  };

  if (selected?.entity_type === "option") return <OptionDetail detail={selected} onNavigate={navigate} onBack={backToResults} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} draftId={draftId} draftMutable={draftMutable} onChanged={onChanged} />;
  if (selected?.entity_type === "group") return <GroupDetail detail={selected} onNavigate={navigate} onBack={backToResults} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} draftId={draftId} draftMutable={draftMutable} onChanged={onChanged} />;
  if (selected?.entity_type === "section") return <SectionDetail detail={selected} onNavigate={navigate} onBack={backToResults} />;
  if (selected?.entity_type === "rule") return <RuleDetail detail={selected} onNavigate={navigate} onBack={backToResults} />;

  const visible = results.filter((row) => mode !== "groups" || row.entity_type === "group");
  return (
    <section className="explorer-workspace">
      <div className="workspace-hero">
        <div>
          <span className="eyebrow">Read-only connected view</span>
          <h2>{mode === "groups" ? "Groups" : "Options & Relationships"}</h2>
          <p>Search the selected model. Canonical IDs and workbook lineage stay under Technical details.</p>
        </div>
        <div className="readonly-label"><LockKeyhole size={14} /> Reference only</div>
      </div>
      <label className="explorer-search">
        <Search size={16} />
        <span className="sr-only">Search options, groups, sections, and rules</span>
        <input autoFocus className="text" value={query} onChange={(e) => search(e.target.value)} placeholder="Search by RPO, name, group, section, rule, or ID…" />
      </label>
      {error && <div className="notice err">{error}</div>}
      {detailError && <div className="notice err">{detailError}</div>}
      {detailError && navigation.type && (
        <button className="btn small" onClick={backToResults}>Return to results</button>
      )}
      <div className="search-results" aria-live="polite">
        {visible.map((row) => (
          <EntityLink key={`${row.entity_type}:${row.entity_id}`} destination={row.destination} onNavigate={navigate}>
            <span className={`result-type ${row.entity_type}`}>{row.entity_type}</span>
            <strong>{row.label}</strong><span>{row.context}</span>
          </EntityLink>
        ))}
      </div>
      <h3>Named diagnostics</h3>
      <div className="diagnostic-grid">
        {diagnostics.map((item) => (
          <button
            key={item.key}
            disabled={item.key === "where_used" || item.key === "option_relationships"}
            title={(item.key === "where_used" || item.key === "option_relationships")
              ? "Open an option first to run this option-specific diagnostic."
              : item.definition}
            onClick={() => runDiagnostic(item)}
          >
            <strong>{item.label}</strong><span>{item.definition}</span>
          </button>
        ))}
      </div>
      <DiagnosticResults result={diagnosticResult} onNavigate={navigate} />
    </section>
  );
}
