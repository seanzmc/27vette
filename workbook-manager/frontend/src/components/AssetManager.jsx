import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, CheckCircle2, ExternalLink, Image, Images,
  RefreshCw, SearchX,
} from "lucide-react";
import { api } from "../api.js";

const PAGE_SIZE = 24;
const STATUS_LABELS = {
  safe_proposal: "Safe proposals",
  covered: "Covered",
  missing: "Missing",
  ambiguous: "Ambiguous",
  unmatched: "Unmatched media",
  unparseable: "Unparseable media",
  dead_url: "Dead URLs",
  stale_target: "Stale targets",
  wildcard_conflict: "Wildcard conflicts",
};
const POSITION_CHOICES = [
  ["left top", "↖"], ["center top", "↑"], ["right top", "↗"],
  ["left center", "←"], ["center", "•"], ["right center", "→"],
  ["left bottom", "↙"], ["center bottom", "↓"], ["right bottom", "↘"],
];

function safeFit(value) {
  return ["cover", "contain", "swatch"].includes(value) ? value : "cover";
}

function safePosition(value) {
  const position = String(value || "center").trim();
  return position && /^[\w\s.%/-]+$/.test(position) ? position : "center";
}

function shortHash(value) {
  return value ? `${value.slice(0, 10)}…${value.slice(-6)}` : "—";
}

function ImagePane({ label, values, fallbackAlt = "", lazy = false }) {
  const url = values?.image_url || "";
  const [state, setState] = useState(url ? "loading" : "empty");
  useEffect(() => setState(url ? "loading" : "empty"), [url]);
  const fit = safeFit(values?.image_fit);
  const position = safePosition(values?.image_position);
  return (
    <div className="asset-image-pane">
      <div className="asset-image-label">
        <strong>{label}</strong>
        {url && (
          <a href={url} target="_blank" rel="noreferrer">
            Open original <ExternalLink size={11} />
          </a>
        )}
      </div>
      <div className={`asset-media-frame fit-${fit}`}>
        {url && state !== "broken" ? (
          <img
            src={url}
            alt={values?.image_alt || fallbackAlt}
            loading={lazy ? "lazy" : "eager"}
            decoding="async"
            style={{ objectPosition: position }}
            onLoad={() => setState("loaded")}
            onError={() => setState("broken")}
          />
        ) : (
          <div className="asset-image-placeholder">
            {state === "broken" ? <AlertTriangle size={22} /> : <Image size={22} />}
            <span>{state === "broken" ? "Image failed to load" : "No image"}</span>
          </div>
        )}
        {state === "loading" && <span className="asset-image-loading">Loading…</span>}
      </div>
      <div className="asset-url mono" title={url}>{url || "No URL"}</div>
      <div className="muted">Alt: {values?.image_alt || fallbackAlt || "not authored"}</div>
    </div>
  );
}

function CoverageCard({ label, value, onClick }) {
  return (
    <button className="coverage-card" onClick={onClick} type="button">
      <span>{label}</span>
      <strong>{value.coverage_pct}%</strong>
      <small>{value.covered} covered · {value.missing} missing · {value.total_targets} total</small>
      <i style={{ width: `${value.coverage_pct}%` }} />
    </button>
  );
}

function QueueThumbnail({ item }) {
  const url = item.proposed_values?.image_url || item.current_values?.image_url ||
    item.candidate?.alternatives?.[0]?.url || "";
  const [broken, setBroken] = useState(false);
  useEffect(() => setBroken(false), [url]);
  return (
    <div className="asset-queue-thumb">
      {url && !broken ? (
        <img src={url} alt="" loading="lazy" decoding="async" onError={() => setBroken(true)} />
      ) : broken ? <AlertTriangle size={18} /> : <Image size={18} />}
    </div>
  );
}

export default function AssetManager({ models, modelKey, setModelKey }) {
  const [filters, setFilters] = useState({
    model: modelKey || "", section: "", target_type: "",
    coverage_intent: "", status: "",
  });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    setLoading(true);
    setError("");
    try {
      const result = await api.assetReconciliation({
        ...filters, offset, limit: PAGE_SIZE, refresh,
      });
      setData(result);
      setSelectedId((current) => (
        result.queue.items.some((item) => item.id === current)
          ? current : result.queue.items[0]?.id || ""
      ));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => { load(false); }, [load]);

  const updateFilter = (key, value) => {
    setFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === "model" ? { section: "" } : {}),
    }));
    if (key === "model" && value) setModelKey(value);
    setOffset(0);
    setSelectedId("");
  };
  const selected = data?.queue.items.find((item) => item.id === selectedId) || null;
  const activeModelCoverage = data?.coverage.models.find(
    (model) => model.model_key === filters.model
  );

  return (
    <div className="asset-workspace">
      <div className="asset-hero">
        <div>
          <div className="eyebrow">Read-only reconciliation intelligence</div>
          <h2>Asset Resolution Workspace</h2>
          <p>See what is covered, what the sync engine can match, and how workbook-owned presentation values render before any decision enters a draft.</p>
        </div>
        <button className="btn" disabled={loading} onClick={() => load(true)} type="button">
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh inventory
        </button>
      </div>
      <div className="notice warn asset-readonly-notice">
        Preview only. Nothing here creates a draft operation, changes the workbook, or modifies WordPress media.
      </div>

      {error && <div className="notice err">Asset reconciliation failed: {error}</div>}
      {!data && loading && <div className="empty">Loading the shared reconciliation view…</div>}
      {data && (
        <>
          <div className="asset-fingerprint-bar">
            <span className="chip blue">{data.media.source}</span>
            <span>{data.media.url_count} media URLs</span>
            <span>workbook <span className="mono">{shortHash(data.fingerprints.workbook_sha256)}</span></span>
            <span>inventory <span className="mono">{shortHash(data.fingerprints.media_inventory_sha256)}</span></span>
            <span>reconciliation <span className="mono">{shortHash(data.fingerprints.reconciliation_sha256)}</span></span>
          </div>

          <div className="section-heading"><CheckCircle2 size={14} /> Coverage dashboard</div>
          <div className="asset-coverage-grid">
            <CoverageCard label={filters.model || "All promoted models"} value={data.coverage.overall} />
            {(activeModelCoverage?.sections || data.coverage.models).map((row) => (
              <CoverageCard
                key={row.section_id || row.model_key}
                label={row.section_id || row.model_key}
                value={row}
                onClick={() => row.section_id
                  ? updateFilter("section", row.section_id)
                  : updateFilter("model", row.model_key)}
              />
            ))}
          </div>

          <div className="asset-status-grid" aria-label="Reconciliation status queues">
            {Object.entries(STATUS_LABELS).map(([key, label]) => (
              <button
                type="button"
                key={key}
                className={filters.status === key ? "active" : ""}
                onClick={() => updateFilter("status", filters.status === key ? "" : key)}
              >
                <strong>{data.status_counts[key] || 0}</strong><span>{label}</span>
              </button>
            ))}
          </div>

          <div className="section-heading"><Images size={14} /> Resolution inbox</div>
          <div className="panel">
            <div className="panel-head asset-filter-bar">
              <select className="select" value={filters.model} onChange={(e) => updateFilter("model", e.target.value)}>
                <option value="">All models</option>
                {models.map((model) => <option key={model.model_key} value={model.model_key}>{model.label}</option>)}
              </select>
              <select className="select" value={filters.section} onChange={(e) => updateFilter("section", e.target.value)}>
                <option value="">All sections</option>
                {data.facets.sections.map((section) => <option key={section} value={section}>{section}</option>)}
              </select>
              <select className="select" value={filters.target_type} onChange={(e) => updateFilter("target_type", e.target.value)}>
                <option value="">All target types</option>
                {data.facets.target_types.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <select className="select" value={filters.coverage_intent} onChange={(e) => updateFilter("coverage_intent", e.target.value)}>
                <option value="">Expected + not expected</option>
                {data.facets.coverage_intents.map((intent) => <option key={intent} value={intent}>{intent}</option>)}
              </select>
              <button className="btn small" type="button" onClick={() => {
                setFilters({ model: "", section: "", target_type: "", coverage_intent: "", status: "" });
                setOffset(0);
              }}>Clear filters</button>
              <span className="spacer" />
              <span className="muted">{data.queue.total} item(s)</span>
            </div>
            {data.queue.items.length ? (
              <div className="asset-inbox-list">
                {data.queue.items.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    className={`asset-inbox-item ${selectedId === item.id ? "selected" : ""}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <QueueThumbnail item={item} />
                    <span className="asset-inbox-copy">
                      <span><b>{item.rpo?.toUpperCase() || item.label}</b> · {item.label}</span>
                      <small>{item.model_key || "unscoped"} · {item.section_id} · {item.target_type}</small>
                      <small className="mono">{item.target_id || item.candidate?.alternatives?.[0]?.url}</small>
                    </span>
                    <span className={`chip asset-status-${item.status}`}>{STATUS_LABELS[item.status] || item.status}</span>
                    <span className="asset-inbox-lineage">
                      {item.lineage.asset_source_row
                        ? `asset_map:${item.lineage.asset_source_row} · ${item.coverage.kind}`
                        : item.lineage.target_source_sheet || "media inventory"}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty"><SearchX size={18} /> No items match these filters.</div>
            )}
            <div className="asset-pagination">
              <button className="btn small" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
              <span className="muted">{data.queue.total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, data.queue.total)}` : "0"} of {data.queue.total}</span>
              <button className="btn small" disabled={offset + PAGE_SIZE >= data.queue.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
            </div>
          </div>

          {selected && <AssetInspector item={selected} />}
        </>
      )}
    </div>
  );
}

function AssetInspector({ item }) {
  const initial = useMemo(() => ({
    ...item.proposed_values,
    image_url: item.proposed_values?.image_url || item.candidate?.alternatives?.[0]?.url || "",
    image_fit: safeFit(item.proposed_values?.image_fit),
    image_position: safePosition(item.proposed_values?.image_position),
    hover_image_position: safePosition(item.proposed_values?.hover_image_position || item.proposed_values?.image_position),
  }), [item]);
  const [preview, setPreview] = useState(initial);
  const [showHover, setShowHover] = useState(false);
  const [previewBroken, setPreviewBroken] = useState(false);
  useEffect(() => { setPreview(initial); setShowHover(false); }, [initial]);
  const displayed = showHover && preview.hover_image_url
    ? { ...preview, image_url: preview.hover_image_url, image_alt: preview.hover_image_alt, image_position: preview.hover_image_position }
    : preview;
  const positionField = showHover ? "hover_image_position" : "image_position";
  useEffect(() => setPreviewBroken(false), [displayed.image_url]);
  return (
    <div className="asset-inspector panel">
      <div className="panel-head">
        <div>
          <strong>{item.rpo?.toUpperCase() || item.label} · {item.label}</strong>
          <div className="muted">{item.model_key || "unscoped"} / {item.section_id} / {item.target_id || item.kind}</div>
        </div>
        <span className={`chip asset-status-${item.status}`}>{STATUS_LABELS[item.status] || item.status}</span>
      </div>
      <div className="panel-body">
        <div className="asset-reason-grid">
          <div><span>Engine decision</span><strong>{item.action}</strong></div>
          <div><span>Candidate source</span><strong>{item.candidate.source || "none"}</strong></div>
          <div><span>Priority</span><strong>{item.candidate.priority ?? "n/a"}</strong></div>
          <div><span>Coverage</span><strong>{item.coverage.kind} · {item.coverage_intent}</strong></div>
        </div>
        <p className="muted">{item.candidate.reason || item.coverage_intent_reason || "The current asset already matches the selected candidate."}</p>
        {item.candidate.alternatives.length > 0 && (
          <details className="asset-alternatives">
            <summary>{item.candidate.alternatives.length} equal-priority / inventory candidate(s)</summary>
            {item.candidate.alternatives.map((candidate) => (
              <button
                type="button"
                key={`${candidate.field}:${candidate.url}`}
                onClick={() => setPreview((current) => ({ ...current, [candidate.field]: candidate.url }))}
              >
                <span>{candidate.field} · {candidate.source} · priority {candidate.priority ?? "n/a"}</span>
                <span className="mono">{candidate.url}</span>
              </button>
            ))}
          </details>
        )}

        <div className="asset-compare-grid">
          <ImagePane label="Current workbook image" values={item.current_values} fallbackAlt={item.label} />
          <ImagePane label="Selected candidate" values={item.proposed_values} fallbackAlt={item.label} />
        </div>

        <div className="asset-preview-layout">
          <div className="asset-preview-controls">
            <div className="eyebrow">Temporary browser controls</div>
            <label>Fit
              <select className="select" value={safeFit(preview.image_fit)} onChange={(e) => setPreview({ ...preview, image_fit: e.target.value })}>
                <option value="cover">cover · fill and crop</option>
                <option value="contain">contain · show full image</option>
                <option value="swatch">swatch · 3:1 color strip</option>
              </select>
            </label>
            <label>{showHover ? "Hover position picker" : "Position picker"}</label>
            <div className="position-picker">
              {POSITION_CHOICES.map(([value, symbol]) => (
                <button className={safePosition(preview[positionField]) === value ? "active" : ""} type="button" key={value} title={value} onClick={() => setPreview({ ...preview, [positionField]: value })}>{symbol}</button>
              ))}
            </div>
            <label>{showHover ? "Advanced hover position" : "Advanced position"}
              <input className="text" value={preview[positionField] || ""} onChange={(e) => setPreview({ ...preview, [positionField]: e.target.value })} />
              <small>Invalid CSS values preview as <span className="mono">center</span>, matching runtime sanitation.</small>
            </label>
            {item.supports_hover && preview.hover_image_url && (
              <label className="hover-toggle">
                <input type="checkbox" checked={showHover} onChange={(e) => setShowHover(e.target.checked)} />
                Show body-style hover media
              </label>
            )}
          </div>
          <div className="asset-card-preview">
            <div className="eyebrow">Card presentation preview · not regenerated runtime proof</div>
            <div className={`runtime-card-media fit-${safeFit(preview.image_fit)} ${showHover ? "show-hover" : ""}`}>
              {displayed.image_url && !previewBroken ? (
                <img
                  src={displayed.image_url}
                  alt={displayed.image_alt || item.label}
                  style={{ objectPosition: safePosition(displayed.image_position) }}
                  onError={() => setPreviewBroken(true)}
                />
              ) : <div className="asset-image-placeholder">
                {previewBroken ? <AlertTriangle size={24} /> : <Image size={24} />}
                <span>{previewBroken ? "Preview image failed to load" : "No preview image"}</span>
              </div>}
            </div>
            <strong>{item.label}</strong>
            <span className="muted">{item.rpo?.toUpperCase() || item.target_type}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
