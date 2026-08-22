import React, { useEffect, useRef, useState } from "react";
import { ArrowLeft, ExternalLink, LockKeyhole, Search } from "lucide-react";
import { api } from "../api.js";

function TechnicalDetails({ data }) {
  if (!data) return null;
  return (
    <details className="technical-details">
      <summary>Technical details</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function EntityLink({ destination, children, onNavigate }) {
  return (
    <button className="entity-link" onClick={() => onNavigate(destination)}>
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

function GroupDetail({ detail, onNavigate, onBack, onDiagnostic, diagnosticResult }) {
  return (
    <section className="explorer-detail" aria-labelledby="group-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference only · workbook-authored group</div>
      <h2 id="group-detail-heading">{detail.label}</h2>
      <p>{detail.notes || "No explanatory notes are authored for this group."}</p>
      <div className="detail-facts">
        <span><strong>Type</strong>{detail.group_type}</span>
        <span><strong>Behavior</strong>{detail.behavior?.replaceAll("_", " ")}</span>
        <span><strong>Members</strong>{detail.member_count}</span>
      </div>
      <div className="detail-actions">
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
    </section>
  );
}

function OptionDetail({ detail, onNavigate, onBack, onDiagnostic, diagnosticResult }) {
  const { option } = detail;
  return (
    <section className="explorer-detail" aria-labelledby="option-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference only · editing arrives in Checkpoint 3</div>
      <h2 id="option-detail-heading">{option.label}</h2>
      <p>{option.description || option.detail_raw || "No additional customer copy is authored."}</p>
      <div className="detail-facts">
        <span><strong>Section</strong>{detail.section?.section_name || "Unmapped"}</span>
        <span><strong>Base price</strong>{option.price === null ? "Not specified" : `$${Number(option.price).toLocaleString()}`}</span>
        <span><strong>Selectable</strong>{option.selectable === "True" ? "Yes" : "No"}</span>
        <span><strong>Active</strong>{option.active === "True" ? "Yes" : "No"}</span>
      </div>
      <div className="detail-actions">
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

export default function ConnectedExplorer({ mode, modelKey }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [diagnostics, setDiagnostics] = useState([]);
  const [diagnosticResult, setDiagnosticResult] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef(null);

  const navigate = async (destination) => {
    try {
      setError("");
      setDiagnosticResult(null);
      if (destination.entity_type === "option") {
        setSelected(await api.connectedOption(modelKey, destination.entity_id));
      } else if (destination.entity_type === "group") {
        const [type, ...id] = destination.entity_id.split(":");
        setSelected(await api.connectedGroup(modelKey, type, id.join(":")));
      } else if (destination.entity_type === "section") {
        setSelected(await api.connectedSection(modelKey, destination.entity_id));
      } else if (destination.entity_type === "rule") {
        setSelected(await api.connectedRule(modelKey, destination.entity_id));
      } else {
        setError(`${destination.entity_type} results remain read-only in Checkpoint 1.`);
      }
    } catch (e) { setError(e.message); }
  };

  useEffect(() => {
    setSelected(null); setResults([]); setQuery(""); setDiagnosticResult(null);
    api.explorerDiagnostics(modelKey).then((data) => setDiagnostics(data.diagnostics)).catch((e) => setError(e.message));
  }, [modelKey]);

  useEffect(() => () => clearTimeout(timer.current), []);

  const search = (value) => {
    setQuery(value); clearTimeout(timer.current);
    if (!value.trim()) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      try { setResults((await api.explorerSearch(modelKey, value)).results); setError(""); }
      catch (e) { setError(e.message); }
    }, 180);
  };

  const runDiagnostic = async (item, entityId = "") => {
    try {
      const data = await api.explorerDiagnostic(modelKey, item.key, { entityId, limit: 100 });
      setDiagnosticResult(data); setError("");
    } catch (e) { setError(e.message); }
  };

  const runEntityDiagnostic = (key, entityId) => runDiagnostic({ key }, entityId);

  if (selected?.entity_type === "option") return <OptionDetail detail={selected} onNavigate={navigate} onBack={() => { setSelected(null); setDiagnosticResult(null); }} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} />;
  if (selected?.entity_type === "group") return <GroupDetail detail={selected} onNavigate={navigate} onBack={() => { setSelected(null); setDiagnosticResult(null); }} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} />;
  if (selected?.entity_type === "section") return <SectionDetail detail={selected} onNavigate={navigate} onBack={() => setSelected(null)} />;
  if (selected?.entity_type === "rule") return <RuleDetail detail={selected} onNavigate={navigate} onBack={() => setSelected(null)} />;

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
