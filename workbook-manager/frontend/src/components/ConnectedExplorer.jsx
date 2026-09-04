import React, { useEffect, useRef, useState } from "react";
import { ArrowLeft, ExternalLink, LockKeyhole, Pencil, Search } from "lucide-react";
import { api } from "../api.js";
import { humanize } from "../naming.js";
import { navigationForDestination } from "../navigationState.js";
import { effectiveValue, overlayBlockReason } from "../draftOverlayModel.js";
import DraftOverlay, { EffectiveText } from "./DraftOverlay.jsx";
import GroupEditor from "./GroupEditor.jsx";
import OptionEditor from "./OptionEditor.jsx";

const OPTION_IMPACT_LABELS = {
  availability: "Availability rows",
  groups: "Groups",
  rules: "Rules",
  pricing: "Pricing rules",
  variant_overrides: "Variant overrides",
  default_rules: "Default rules",
  assets: "Images",
};

function TechnicalDetails({ data }) {
  if (!data) return null;
  return (
    <details className="technical-details">
      <summary>Technical details</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

// Edit buttons stay disabled for a locked draft or a blocked (stale/terminal)
// overlay; the exact reason is the tooltip (EFFECTIVE-04).
function editDisabledReason(draftMutable, overlay) {
  if (!draftMutable) return "The active draft is locked; start a new draft to edit.";
  return overlayBlockReason(overlay);
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
      <p className="muted">Parameters: model {result.model_key}{result.entity_id ? ` · entity ${result.entity_id}` : ""}</p>
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
  const overlay = detail.draft_overlay;
  const blocked = editDisabledReason(draftMutable, overlay);
  return (
    <section className="explorer-detail" aria-labelledby="group-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference view · edits save to the durable draft</div>
      <h2 id="group-detail-heading">
        <EffectiveText overlay={overlay} field="display_label" authored={detail.label} />
      </h2>
      <DraftOverlay overlay={overlay} impactLabels={{ members: "Members" }} testId="group-draft-overlay" />
      <p><EffectiveText overlay={overlay} field="notes" authored={detail.notes || "No explanatory notes are authored for this group."} /></p>
      <div className="detail-facts">
        <span><strong>Type</strong>{humanize(detail.group_type)}</span>
        <span><strong>Behavior</strong><EffectiveText overlay={overlay} field={detail.group_type === "exclusive" ? "selection_mode" : "group_type"} authored={detail.behavior} format={humanize} /></span>
        <span><strong>Active</strong><EffectiveText overlay={overlay} field="active" authored={detail.active ? "Yes" : "No"} /></span>
        <span><strong>Members</strong>{detail.member_count}</span>
      </div>
      <div className="detail-actions">
        <button
          className="btn small"
          disabled={Boolean(blocked)}
          title={blocked || "Edit registered group fields in the durable draft"}
          onClick={() => setEditing("facts")}
        >
          <Pencil size={14} /> Edit group in draft
        </button>
        <button
          className="btn small"
          disabled={Boolean(blocked)}
          title={blocked || "Add, remove, activate, or reorder members in the durable draft"}
          onClick={() => setEditing("members")}
        >
          <Pencil size={14} /> Manage members in draft
        </button>
        {blocked && <span className="muted">{draftMutable ? "Editing blocked — see the draft notice above." : "Draft locked — editing unavailable."}</span>}
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
      <TechnicalDetails data={{ group_id: detail.group_id, group: detail.group, ...detail.technical }} />
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
  const overlay = detail.draft_overlay;
  const blocked = editDisabledReason(draftMutable, overlay);
  // The heading is the RPO — name pair; when the draft changes either half, the
  // heading shows the authored label struck through beside the proposed label.
  const proposedLabel = [
    effectiveValue(overlay, "rpo", option.rpo),
    effectiveValue(overlay, "option_name", option.option_name),
  ].map((part) => String(part ?? "").trim()).filter(Boolean).join(" — ") || option.label;
  const price = (value) => (value === null || value === undefined || value === ""
    ? "Not specified" : `$${Number(value).toLocaleString()}`);
  const yesNo = (value) => (value === "True" ? "Yes" : "No");
  const copyField = overlay?.changed_fields?.description ? "description" : "detail_raw";
  return (
    <section className="explorer-detail" aria-labelledby="option-detail-heading">
      <button className="btn small" onClick={onBack}><ArrowLeft size={14} /> Back to results</button>
      <div className="readonly-label"><LockKeyhole size={14} /> Reference view · edits save to the durable draft</div>
      <h2 id="option-detail-heading">
        {proposedLabel !== option.label
          ? <span className="effective-text" data-field="label"><s className="authored-value">{option.label}</s><span className="proposed-value">{proposedLabel}</span></span>
          : option.label}
      </h2>
      <DraftOverlay overlay={overlay} impactLabels={OPTION_IMPACT_LABELS} testId="option-draft-overlay" />
      <p><EffectiveText overlay={overlay} field={copyField} authored={option.description || option.detail_raw || "No additional customer copy is authored."} /></p>
      <div className="detail-facts">
        <span><strong>Section</strong><EffectiveText overlay={overlay} field="section_id" authored={detail.section?.section_name || "Unmapped"} /></span>
        <span><strong>Base price</strong><EffectiveText overlay={overlay} field="price" authored={option.price} format={price} /></span>
        <span><strong>Selectable</strong><EffectiveText overlay={overlay} field="selectable" authored={option.selectable} format={yesNo} /></span>
        <span><strong>Active</strong><EffectiveText overlay={overlay} field="active" authored={option.active} format={yesNo} /></span>
      </div>
      <div className="detail-actions">
        <button
          className="btn small"
          disabled={Boolean(blocked)}
          title={blocked || "Edit this option in the durable draft"}
          onClick={() => setEditing(true)}
        >
          <Pencil size={14} /> Edit option in draft
        </button>
        {blocked && <span className="muted">{draftMutable ? "Editing blocked — see the draft notice above." : "Draft locked — editing unavailable."}</span>}
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
            <strong>{group.label}</strong><span>{humanize(group.behavior)} · {group.member_count} members</span>
          </EntityLink>
        ))}
        {!detail.exclusive_groups.length && !detail.rule_groups.length && <p className="muted">No connected groups.</p>}
      </div>
      <h3>Rules</h3>
      <div className="relationship-list compact">
        {detail.rules.map((rule) => (
          <div key={rule.rule_id}><strong>{humanize(rule.rule_type)}</strong><span>{rule.source_rpo || rule.source_id} → {rule.target_rpo || rule.target_id}</span></div>
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
      <TechnicalDetails data={{ ...detail.technical, rules: detail.rules }} />
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
      <h2 id="rule-detail-heading">{humanize(detail.rule.rule_type)}</h2>
      <div className="relationship-list">
        {source && <EntityLink destination={{ workspace: "options", entity_type: "option", entity_id: source.option_id }} onNavigate={onNavigate}><strong>{source.rpo} — {source.option_name}</strong><span>Source option</span></EntityLink>}
        {target && <EntityLink destination={{ workspace: "options", entity_type: "option", entity_id: target.option_id }} onNavigate={onNavigate}><strong>{target.rpo} — {target.option_name}</strong><span>Target option</span></EntityLink>}
      </div>
      <TechnicalDetails data={{ ...detail.technical, rule: detail.rule }} />
    </section>
  );
}

export default function ConnectedExplorer({
  mode, modelKey, navigation, onNavigationChange,
  draftId, draftRevision, draftMutable, onChanged,
}) {
  const [results, setResults] = useState([]);
  const [searchPage, setSearchPage] = useState(null);
  const [groupPage, setGroupPage] = useState(null);
  const [selected, setSelected] = useState(null);
  const [diagnostics, setDiagnostics] = useState([]);
  const [diagnosticResult, setDiagnosticResult] = useState(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const timer = useRef(null);
  const detailRequest = useRef(0);
  const searchRequest = useRef(0);
  const groupRequest = useRef(0);
  const preDiagnostic = useRef(null);
  const query = navigation.query;
  const diagnosticKey = navigation.diagnostic || "";
  const diagnosticEntity = navigation.diagnostic_entity || "";
  const groupType = navigation.group_type || "all";
  const offset = navigation.offset || 0;

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
    // A generation counter ignores any response whose request parameters are
    // no longer current: an older index request resolving after a newer one
    // (model, group type, or page switched mid-flight) must never overwrite
    // groupPage or error with the superseded model's rows.
    const generation = ++groupRequest.current;
    if (mode !== "groups" || query.trim() || diagnosticKey || navigation.type) {
      setGroupPage(null);
      return;
    }
    api.explorerGroups(modelKey, { groupType, offset, limit: 24 })
      .then((data) => {
        if (generation !== groupRequest.current) return;
        setGroupPage(data);
        setError("");
      })
      .catch((e) => {
        if (generation !== groupRequest.current) return;
        setGroupPage(null);
        setError(e.message);
      });
  }, [mode, modelKey, groupType, offset, query, diagnosticKey, navigation.type]);

  useEffect(() => {
    const generation = ++searchRequest.current;
    if (!query.trim() || diagnosticKey) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      try {
        // In the Groups workspace the search is scoped server-side to group
        // entities before pagination, so a page cannot be filled (or emptied)
        // by other entity types outranking the matching groups.
        const data = await api.explorerSearch(modelKey, query, {
          offset, limit: 40, entityType: mode === "groups" ? "group" : "",
        });
        if (generation !== searchRequest.current) return;
        setResults(data.results);
        setSearchPage(data);
        setError("");
      } catch (e) {
        if (generation === searchRequest.current) setError(e.message);
      }
    }, 180);
    return () => clearTimeout(timer.current);
  }, [mode, modelKey, query, offset, diagnosticKey]);

  useEffect(() => {
    if (!diagnosticKey || navigation.type) {
      setDiagnosticResult(null);
      return;
    }
    api.explorerDiagnostic(modelKey, diagnosticKey, { entityId: diagnosticEntity, offset, limit: 100 })
      .then((data) => { setDiagnosticResult(data); setResults([]); setError(""); })
      .catch((e) => { setDiagnosticResult(null); setError(e.message); });
  }, [modelKey, diagnosticKey, diagnosticEntity, offset, navigation.type]);

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
    onNavigationChange({
      ...navigation, query: value, diagnostic: "", diagnostic_entity: "", offset: 0,
    }, { replace: true });
  };

  const runDiagnostic = async (item, entityId = "") => {
    // Retain the exact pre-diagnostic navigation (query, offset, model, and
    // workspace) so "Back to results" restores the documented prior index or
    // search state instead of a cleared, unfiltered one.
    preDiagnostic.current = navigation;
    onNavigationChange({
      ...navigation, type: "", id: "", query: "", offset: 0, diagnostic: item.key,
      diagnostic_entity: entityId,
    });
  };

  const runEntityDiagnostic = (key, entityId) => runDiagnostic({ key }, entityId);

  const backToIndex = () => {
    // Restore the exact retained pre-diagnostic index/search navigation (with
    // replace, so the diagnostic adds no extra history entry); deep-linked
    // diagnostics have no retained state and fall back to the model index.
    if (preDiagnostic.current) {
      onNavigationChange({ ...preDiagnostic.current }, { replace: true });
      preDiagnostic.current = null;
      return;
    }
    onNavigationChange({ ...navigation, diagnostic: "", diagnostic_entity: "" });
  };

  const backToResults = () => {
    const previous = window.history.state?.returnNavigation;
    if (previous) {
      window.history.back();
    } else if (diagnosticKey && preDiagnostic.current) {
      // Replace the diagnostic entry with the retained pre-diagnostic
      // navigation: the prior index/search returns exactly and no extra
      // history entry accumulates behind it.
      onNavigationChange({ ...preDiagnostic.current }, { replace: true });
      preDiagnostic.current = null;
    } else {
      onNavigationChange({ ...navigation, type: "", id: "" });
    }
  };

  if (selected?.entity_type === "option") return <OptionDetail detail={selected} onNavigate={navigate} onBack={backToResults} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} draftId={draftId} draftMutable={draftMutable} onChanged={onChanged} />;
  if (selected?.entity_type === "group") return <GroupDetail detail={selected} onNavigate={navigate} onBack={backToResults} onDiagnostic={runEntityDiagnostic} diagnosticResult={diagnosticResult} draftId={draftId} draftMutable={draftMutable} onChanged={onChanged} />;
  if (selected?.entity_type === "section") return <SectionDetail detail={selected} onNavigate={navigate} onBack={backToResults} />;
  if (selected?.entity_type === "rule") return <RuleDetail detail={selected} onNavigate={navigate} onBack={backToResults} />;

  const visible = query.trim()
    ? results.filter((row) => mode !== "groups" || row.entity_type === "group")
    : (mode === "groups" ? (groupPage?.results || []) : []);
  const diagnostic = diagnostics.find((item) => item.key === diagnosticKey);
  if (diagnosticKey && !navigation.type) {
    return (
      <section className="explorer-workspace" aria-labelledby="diagnostics-heading">
        <button className="btn small" onClick={backToIndex}><ArrowLeft size={14} /> Back to results</button>
        <div className="workspace-hero">
          <div><span className="eyebrow">Read-only connected view</span><h2 id="diagnostics-heading">Diagnostics</h2>
            <p>{diagnostic?.definition || "Run a named diagnostic for the selected model."}</p></div>
          <div className="readonly-label"><LockKeyhole size={14} /> Reference only</div>
        </div>
        {error && <div className="notice err">{error}</div>}
        {!error && !diagnosticResult && <p className="muted">Loading diagnostic results…</p>}
        {diagnosticResult && <DiagnosticResults result={diagnosticResult} onNavigate={navigate} />}
        {diagnosticResult && (offset > 0 || diagnosticResult.has_more) && (
          <div className="explorer-pagination">
            <button className="btn small" disabled={!offset} onClick={() => onNavigationChange({ ...navigation, offset: Math.max(0, offset - 100) })}>Previous</button>
            <span>Results {offset + 1}–{offset + diagnosticResult.results.length}</span>
            <button className="btn small" disabled={!diagnosticResult.has_more} onClick={() => onNavigationChange({ ...navigation, offset: offset + 100 })}>Next</button>
          </div>
        )}
      </section>
    );
  }
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
      {mode === "groups" && !query.trim() && (
        <label className="explorer-filter">Group type
          <select value={groupType} onChange={(event) => onNavigationChange({
            ...navigation, group_type: event.target.value, offset: 0,
          })}>
            <option value="all">All groups</option><option value="exclusive">Exclusive groups</option>
            <option value="rule">Rule groups</option>
          </select>
        </label>
      )}
      {error && <div className="notice err">{error}</div>}
      {detailError && <div className="notice err">{detailError}</div>}
      {detailError && navigation.type && (
        <button className="btn small" onClick={backToResults}>Return to results</button>
      )}
      <div className="search-results" aria-live="polite">
        {visible.map((row) => (
          <EntityLink key={`${row.entity_type}:${row.entity_id}`} destination={row.destination} onNavigate={navigate}>
            <span className={`result-type ${row.entity_type}`}>{row.entity_type}</span>
            <strong>{row.label}</strong>
            <span>{query.trim()
              ? <><span>{row.context}</span><small>Match reasons: {row.match_reasons.map((reason) => `${reason.class} · ${reason.field}`).join(", ")}</small></>
              : <>{row.group_id} · {row.member_count} members · {row.active ? "Active" : "Inactive"}</>}</span>
          </EntityLink>
        ))}
        {mode === "groups" && !query.trim() && groupPage && !visible.length && (
          <p className="muted">No groups match this model and group type.</p>
        )}
      </div>
      {mode === "groups" && !query.trim() && groupPage?.total > groupPage?.limit && (
        <div className="explorer-pagination">
          <button className="btn small" disabled={!offset} onClick={() => onNavigationChange({ ...navigation, offset: Math.max(0, offset - 24) })}>Previous</button>
          <span>{offset + 1}–{offset + visible.length} of {groupPage.total}</span>
          <button className="btn small" disabled={!groupPage.has_more} onClick={() => onNavigationChange({ ...navigation, offset: offset + 24 })}>Next</button>
        </div>
      )}
      {query.trim() && searchPage?.total > searchPage?.limit && (
        <div className="explorer-pagination">
          <button className="btn small" disabled={!offset} onClick={() => onNavigationChange({ ...navigation, offset: Math.max(0, offset - 40) })}>Previous</button>
          <span>{offset + 1}–{offset + visible.length} of {searchPage.total}</span>
          <button className="btn small" disabled={!searchPage.has_more} onClick={() => onNavigationChange({ ...navigation, offset: offset + 40 })}>Next</button>
        </div>
      )}
      <h3>Diagnostics</h3>
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
