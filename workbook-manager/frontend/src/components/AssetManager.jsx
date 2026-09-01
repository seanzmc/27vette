import React, { useCallback, useEffect, useMemo, useState } from "react";
import EditorShell from "./EditorShell.jsx";
import { operatorLifecycle } from "./ChangesSync.jsx";
import {
  AlertTriangle, Ban, CheckCircle2, ExternalLink, Image, Images,
  Link, RefreshCw, Save, SearchX,
} from "lucide-react";
import { api } from "../api.js";
import {
  ALL_MODELS, assetInScope, reconciliationModel,
} from "../assetScope.js";

const PAGE_SIZE = 24;
const LINK_LOOKUP_PAGE_SIZE = 100;
const MEDIA_LOOKUP_PAGE_SIZE = 12;
const TARGET_LOOKUP_PAGE_SIZE = 12;
const EMPTY_FILTERS = {
  section: "", target_type: "", coverage_intent: "", status: "",
};
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
  ignored: "Ignored media",
};
const POSITION_CHOICES = [
  ["left top", "↖"], ["center top", "↑"], ["right top", "↗"],
  ["left center", "←"], ["center", "•"], ["right center", "→"],
  ["left bottom", "↙"], ["center bottom", "↓"], ["right bottom", "↘"],
];
const FIT_DESCRIPTIONS = {
  cover: "fill and crop",
  contain: "show full image",
  swatch: "3:1 color strip",
};

function safeFit(value, choices) {
  return choices.includes(value) ? value : choices[0] || String(value || "");
}

function safePosition(value) {
  const position = String(value || "center").trim();
  return position && /^[\w\s.%/-]+$/.test(position) ? position : "center";
}

function shortHash(value) {
  return value ? `${value.slice(0, 10)}…${value.slice(-6)}` : "—";
}

function ImagePane({ label, values, fitValues, fallbackAlt = "", lazy = false }) {
  const url = values?.image_url || "";
  const [state, setState] = useState(url ? "loading" : "empty");
  useEffect(() => setState(url ? "loading" : "empty"), [url]);
  const fit = safeFit(values?.image_fit, fitValues);
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

async function findLinkedAsset(itemId, draftId) {
  let offset = 0;
  while (true) {
    const result = await api.assetReconciliation({
      offset,
      limit: LINK_LOOKUP_PAGE_SIZE,
      draft_id: draftId,
    });
    const item = result.queue.items.find((candidate) => candidate.id === itemId);
    if (item) return item;
    offset += result.queue.items.length;
    if (!result.queue.items.length || offset >= result.queue.total) return null;
  }
}

export default function AssetManager({
  modelKey, setModelKey, draftId, draftMutable, draftLifecycle, onChanged,
  navigation, onNavigationChange,
}) {
  // §3F: the open image decision is navigation state, not component state, so it
  // survives reload, is linkable, and is preserved when a draft starts. `assets`
  // was already a workspace; `asset` joins ENTITY_TYPES for the entity half.
  const selectedId = navigation?.type === "asset" ? navigation.id || "" : "";
  const selectAsset = useCallback((id) => {
    onNavigationChange({
      ...navigation,
      workspace: "assets",
      type: id ? "asset" : "",
      id: id || "",
    });
  }, [navigation, onNavigationChange]);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [dataScope, setDataScope] = useState("");
  const [linkedAsset, setLinkedAsset] = useState({ id: "", item: null, loading: false, error: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [actionBusy, setActionBusy] = useState("");
  const requestRef = React.useRef(0);

  const load = useCallback(async (refresh = false) => {
    const requestId = ++requestRef.current;
    const requestedScope = modelKey;
    setLoading(true);
    setError("");
    try {
      const result = await api.assetReconciliation({
        ...filters, model: reconciliationModel(modelKey),
        offset, limit: PAGE_SIZE, refresh, draft_id: draftId,
      });
      if (requestId !== requestRef.current) return;
      setData(result);
      setDataScope(requestedScope);
    } catch (e) {
      if (requestId !== requestRef.current) return;
      setError(e.message);
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }, [filters, offset, draftId, modelKey]);

  useEffect(() => { load(false); }, [load]);
  useEffect(() => {
    setFilters(EMPTY_FILTERS);
    setOffset(0);
  }, [modelKey]);

  const scopedData = dataScope === modelKey ? data : null;
  const queuedSelection = scopedData?.queue.items.find((item) => item.id === selectedId) || null;
  useEffect(() => {
    if (!selectedId || !scopedData || queuedSelection) {
      setLinkedAsset({ id: "", item: null, loading: false, error: "" });
      return undefined;
    }
    let cancelled = false;
    setLinkedAsset((current) => ({
      id: selectedId,
      item: current.id === selectedId ? current.item : null,
      loading: true,
      error: "",
    }));
    findLinkedAsset(selectedId, draftId)
      .then((item) => {
        if (!cancelled) setLinkedAsset({ id: selectedId, item, loading: false, error: "" });
      })
      .catch((lookupError) => {
        if (!cancelled) {
          setLinkedAsset({
            id: selectedId,
            item: null,
            loading: false,
            error: lookupError.message,
          });
        }
      });
    return () => { cancelled = true; };
  }, [selectedId, scopedData, queuedSelection, draftId]);

  const updateFilter = (key, value) => {
    setFilters((current) => ({
      ...current,
      [key]: value,
    }));
    setOffset(0);
    if (selectedId) selectAsset("");
  };
  const selected = queuedSelection || (
    linkedAsset.id === selectedId ? linkedAsset.item : null
  );
  const selectedInScope = assetInScope(selected, modelKey);
  const activeModelCoverage = scopedData?.coverage.models.find(
    (model) => model.model_key === modelKey
  );
  const runResolution = async (label, payload, { bulk = false } = {}) => {
    setActionBusy(label);
    setNotice(null);
    try {
      const result = bulk
        ? await api.saveAllSafeAssetResolutions(draftId, payload)
        : await api.saveAssetResolution(draftId, payload);
      setNotice({
        kind: "ok",
        text: bulk
          ? `${result.accepted} safe asset resolution(s) added to Review & Apply.`
          : "Asset resolution added to the shared durable draft.",
      });
      await onChanged();
      await load(false);
      return result;
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
      return null;
    } finally {
      setActionBusy("");
    }
  };
  const boundPayload = (payload = {}) => ({
    fingerprints: data.fingerprints,
    session_id: "asset-manager",
    actor: "Workbook Manager operator",
    ...payload,
  });

  return (
    <div className="asset-workspace">
      <div className="asset-hero">
        <div>
          <div className="eyebrow">Read-only reconciliation intelligence</div>
          <h2>Asset Resolution Workspace</h2>
          <p>See what is covered, what the sync engine can match, and how workbook-owned presentation values render before any decision enters a draft.</p>
        </div>
        <button className="btn" disabled={loading} onClick={() => load(true)} type="button">
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh WordPress Image Inventory
        </button>
      </div>
      <div className="notice warn asset-readonly-notice">
        Resolutions enter the same durable draft and Review &amp; Apply as ordinary edits. Nothing here writes the workbook or modifies WordPress media.
      </div>

      {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}
      {error && <div className="notice err">Asset reconciliation failed: {error}</div>}
      {!scopedData && loading && <div className="empty">Loading the shared reconciliation view…</div>}
      {scopedData && (
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
            <CoverageCard label={modelKey === ALL_MODELS ? "All promoted models" : modelKey} value={data.coverage.overall} />
            {(activeModelCoverage?.sections || data.coverage.models).map((row) => (
              <CoverageCard
                key={row.section_id || row.model_key}
                label={row.section_id || row.model_key}
                value={row}
                onClick={() => row.section_id
                  ? updateFilter("section", row.section_id)
                  : setModelKey(row.model_key)}
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

          <div className="asset-draft-toolbar panel panel-body">
            <div>
              <strong>Shared draft basket</strong>
              <span className="muted" data-testid="asset-draft-lifecycle">
                {operatorLifecycle[draftLifecycle?.draft?.status] || "Collecting draft changes"}
                {" · "}
                {draftLifecycle?.operations?.length || 0} workbook operation(s) · {data.draft_asset_resolutions?.count || 0} asset evidence record(s)
              </span>
              {data.draft_asset_resolutions?.stale_count > 0 && (
                <span className="chip warn">{data.draft_asset_resolutions.stale_count} stale asset resolution(s)</span>
              )}
            </div>
            <button
              className="btn primary"
              type="button"
              disabled={!draftMutable || !data.status_counts.safe_proposal || !!actionBusy}
              onClick={() => runResolution(
                "accept safe proposals",
                boundPayload({ model: reconciliationModel(modelKey) }),
                { bulk: true },
              )}
            >
              <CheckCircle2 size={14} /> Add all safe matches to draft
            </button>
          </div>

          <div className="section-heading"><Images size={14} /> Resolution inbox</div>
          <div className="panel">
            <div className="panel-head asset-filter-bar">
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
                setFilters(EMPTY_FILTERS);
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
                    onClick={() => selectAsset(item.id)}
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

          {selectedId && !selected && linkedAsset.loading && (
            <div className="notice">Loading the linked image decision…</div>
          )}
          {selectedId && !selected && !linkedAsset.loading && (
            <div className="notice warn">
              {linkedAsset.error
                ? `The linked image decision could not be loaded: ${linkedAsset.error}`
                : "The linked image decision no longer exists in this reconciliation snapshot."}{" "}
              <button className="btn small" type="button" onClick={() => selectAsset("")}>
                Clear the link
              </button>
            </div>
          )}
          {selected && !selectedInScope && (
            <div className="notice warn">
              This image decision belongs to {selected.model_key || "the All models queue"},
              but the visible scope is {modelKey === ALL_MODELS ? "All models" : modelKey}.
              Switch the visible scope before reviewing or changing it.{" "}
              <button
                className="btn small"
                type="button"
                onClick={() => setModelKey(selected.model_key || ALL_MODELS)}
              >
                Switch the visible scope
              </button>
            </div>
          )}
          {selected && selectedInScope && (
            <AssetInspector
              item={selected}
              modelKey={modelKey}
              reconciliationFingerprints={data.fingerprints}
              fitValues={data.controls?.image_fit || []}
              draftMutable={draftMutable}
              drafted={(data.draft_asset_resolutions?.item_ids || []).includes(selected.id)}
              busy={actionBusy}
              onResolve={(payload) => runResolution(
                payload.resolution_kind.replaceAll("_", " "),
                boundPayload({ item_id: selected.id, ...payload }),
              )}
              onClose={() => selectAsset("")}
            />
          )}
        </>
      )}
    </div>
  );
}

function AssetInspector({
  item, modelKey, reconciliationFingerprints, fitValues, draftMutable, drafted,
  busy, onResolve, onClose,
}) {
  const initial = useMemo(() => ({
    ...item.proposed_values,
    image_url: item.proposed_values?.image_url || item.candidate?.alternatives?.[0]?.url || "",
    image_fit: safeFit(item.proposed_values?.image_fit, fitValues),
    image_position: safePosition(item.proposed_values?.image_position),
    hover_image_position: safePosition(item.proposed_values?.hover_image_position || item.proposed_values?.image_position),
  }), [item, fitValues]);
  const [preview, setPreview] = useState(initial);
  const [showHover, setShowHover] = useState(false);
  const [previewBroken, setPreviewBroken] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [targetItemId, setTargetItemId] = useState("");
  const [inventoryQuery, setInventoryQuery] = useState("");
  const [inventoryLookup, setInventoryLookup] = useState({
    status: "idle", error: "", items: [], total: 0, offset: 0, fingerprints: null,
  });
  const [inventoryUrl, setInventoryUrl] = useState("");
  const [targetQuery, setTargetQuery] = useState("");
  const [targetLookup, setTargetLookup] = useState({
    status: "idle", error: "", items: [], total: 0, offset: 0, fingerprints: null,
  });
  useEffect(() => {
    setPreview(initial);
    setShowHover(false);
    setSelectedCandidate("");
    setTargetItemId("");
    setInventoryLookup({ status: "idle", error: "", items: [], total: 0, offset: 0, fingerprints: null });
    setInventoryUrl("");
    setTargetQuery("");
    setTargetLookup({ status: "idle", error: "", items: [], total: 0, offset: 0, fingerprints: null });
  }, [item.id]);
  const displayed = showHover && preview.hover_image_url
    ? { ...preview, image_url: preview.hover_image_url, image_alt: preview.hover_image_alt, image_position: preview.hover_image_position }
    : preview;
  const positionField = showHover ? "hover_image_position" : "image_position";
  useEffect(() => setPreviewBroken(false), [displayed.image_url]);
  const resolutionValues = {
    image_url: preview.image_url || "",
    image_alt: preview.image_alt || "",
    image_fit: safeFit(preview.image_fit, fitValues),
    image_position: safePosition(preview.image_position),
    hover_image_url: preview.hover_image_url || "",
    hover_image_alt: preview.hover_image_alt || "",
    hover_image_position: preview.hover_image_position || "",
    active: preview.active === false || preview.active === "False" ? false : true,
    notes: preview.notes || "",
  };
  const presentationOnly = { ...resolutionValues };
  delete presentationOnly.image_url;
  delete presentationOnly.hover_image_url;
  const searchInventory = async (offset = 0) => {
    setInventoryLookup((current) => ({ ...current, status: "loading", error: "" }));
    try {
      const result = await api.assetMediaOptions(inventoryQuery, {
        offset, limit: MEDIA_LOOKUP_PAGE_SIZE,
      });
      setInventoryLookup({ ...result, status: "ready", error: "" });
    } catch (error) {
      setInventoryLookup((current) => ({
        ...current, status: "error", error: error.message,
      }));
    }
  };
  const searchTargets = async (offset = 0) => {
    setTargetLookup((current) => ({ ...current, status: "loading", error: "" }));
    try {
      const result = await api.assetAssignmentTargets(targetQuery, {
        model: reconciliationModel(modelKey), offset, limit: TARGET_LOOKUP_PAGE_SIZE,
      });
      setTargetLookup({ ...result, status: "ready", error: "" });
    } catch (error) {
      setTargetLookup((current) => ({
        ...current, status: "error", error: error.message,
      }));
    }
  };
  const inventoryStale = inventoryLookup.fingerprints
    && inventoryLookup.fingerprints.media_inventory_sha256
      !== reconciliationFingerprints.media_inventory_sha256;
  const targetsStale = targetLookup.fingerprints
    && targetLookup.fingerprints.reconciliation_sha256
      !== reconciliationFingerprints.reconciliation_sha256;
  // §3C dirty contract: the shell must be able to refuse a silent close while
  // unsaved preview, candidate, inventory, or assignment decisions are pending.
  // Preview is compared against the same `initial` it is seeded from; the three
  // selection controls start empty and remain explicit pending intent even when
  // their selected URL happens to match the seeded preview.
  const dirty = useMemo(
    () => JSON.stringify(preview) !== JSON.stringify(initial)
      || Boolean(selectedCandidate || inventoryUrl || targetItemId),
    [preview, initial, selectedCandidate, inventoryUrl, targetItemId],
  );

  const resolve = (resolution_kind, extra = {}) => onResolve({
    resolution_kind,
    values: resolutionValues,
    selected_url: "",
    target_item_id: "",
    ...extra,
  });
  return (
    <EditorShell
      title={`${item.rpo?.toUpperCase() || item.label} · ${item.label}`}
      subtitle={`${item.model_key || "unscoped"} / ${item.section_id} / ${item.target_id || item.kind}`}
      target="image decision"
      dirty={dirty}
      busy={Boolean(busy)}
      onRequestClose={onClose}
    >
      <div className="asset-inspector">
        <div className="asset-inspector-status">
          <span className={`chip asset-status-${item.status}`}>{STATUS_LABELS[item.status] || item.status}</span>
        </div>
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
                className={selectedCandidate === candidate.url ? "selected" : ""}
                onClick={() => {
                  setSelectedCandidate(candidate.url);
                  setPreview((current) => ({ ...current, [candidate.field]: candidate.url }));
                }}
              >
                <span>{candidate.field} · {candidate.source} · priority {candidate.priority ?? "n/a"}</span>
                <span className="mono">{candidate.url}</span>
              </button>
            ))}
          </details>
        )}

        <div className="asset-compare-grid">
          <ImagePane label="Current workbook image" values={item.current_values} fitValues={fitValues} fallbackAlt={item.label} />
          <ImagePane label="Selected candidate" values={preview} fitValues={fitValues} fallbackAlt={item.label} />
        </div>

        <div className="asset-preview-layout">
          <div className="asset-preview-controls">
            <div className="eyebrow">Temporary browser controls</div>
            <label>Image URL
              <input className="text" value={preview.image_url || ""} onChange={(e) => setPreview({ ...preview, image_url: e.target.value })} />
            </label>
            <label>Image alt text
              <input className="text" value={preview.image_alt || ""} onChange={(e) => setPreview({ ...preview, image_alt: e.target.value })} />
            </label>
            <label>Fit
              <select className="select" value={safeFit(preview.image_fit, fitValues)} onChange={(e) => setPreview({ ...preview, image_fit: e.target.value })}>
                {fitValues.map((fit) => (
                  <option value={fit} key={fit}>{fit} · {FIT_DESCRIPTIONS[fit] || fit}</option>
                ))}
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
            {item.supports_hover && (
              <>
                <label>Hover image URL
                  <input className="text" value={preview.hover_image_url || ""} onChange={(e) => setPreview({ ...preview, hover_image_url: e.target.value })} />
                </label>
                <label>Hover alt text
                  <input className="text" value={preview.hover_image_alt || ""} onChange={(e) => setPreview({ ...preview, hover_image_alt: e.target.value })} />
                </label>
              </>
            )}
            <label className="hover-toggle">
              <input
                type="checkbox"
                checked={resolutionValues.active}
                onChange={(e) => setPreview({ ...preview, active: e.target.checked })}
              />
              Asset row active
            </label>
            <label>Notes
              <textarea className="text" rows="3" value={preview.notes || ""} onChange={(e) => setPreview({ ...preview, notes: e.target.value })} />
            </label>
          </div>
          <div className="asset-card-preview">
            <div className="eyebrow">Card presentation preview · not regenerated runtime proof</div>
            <div className={`runtime-card-media fit-${safeFit(preview.image_fit, fitValues)} ${showHover ? "show-hover" : ""}`}>
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

        <div className="asset-resolution-actions">
          <div>
            <div className="eyebrow">Durable resolution action</div>
            <p className="muted">
              This records exact reconciliation evidence beside the ordinary asset_map draft operation. Review &amp; Apply remains the approval basket.
            </p>
          </div>
          {drafted && (
            <div className="notice ok">This item already has evidence in Review &amp; Apply. Saving again may refine the same physical-row operation, but cannot silently retarget it.</div>
          )}
          {!draftMutable && (
            <div className="notice warn">This draft is no longer mutable. Start a new draft to resolve another asset.</div>
          )}
          {item.status === "safe_proposal" && (
            <button className="btn primary" disabled={!draftMutable || !!busy} onClick={() => resolve("accept_safe")}>
              <CheckCircle2 size={14} /> Add safe proposal to draft
            </button>
          )}
          {item.status === "ambiguous" && (
            <button
              className="btn primary"
              disabled={!draftMutable || !!busy || !selectedCandidate}
              onClick={() => resolve("select_candidate", {
                selected_url: selectedCandidate,
                values: presentationOnly,
              })}
            >
              <Link size={14} /> Use explicitly selected candidate
            </button>
          )}
          {item.status === "missing" && (
            <div className="asset-resolution-stack">
              <label>Search stable media inventory
                <span className="toolbar compact-toolbar">
                  <input className="text" value={inventoryQuery} onChange={(e) => setInventoryQuery(e.target.value)} placeholder="RPO or filename" />
                  <button className="btn small" type="button" disabled={inventoryLookup.status === "loading"} onClick={() => searchInventory(0)}>Search</button>
                </span>
              </label>
              {inventoryLookup.status === "loading" && <div className="notice">Searching media inventory…</div>}
              {inventoryLookup.status === "error" && (
                <div className="notice err">Inventory search failed: {inventoryLookup.error}{" "}
                  <button className="btn small" type="button" onClick={() => searchInventory(inventoryLookup.offset)}>Retry inventory search</button>
                </div>
              )}
              {inventoryStale && <div className="notice warn">The media inventory changed. Search again before selecting an image.</div>}
              {inventoryLookup.status === "ready" && !inventoryLookup.items.length && (
                <div className="empty">No inventory images match this search.</div>
              )}
              {inventoryLookup.items.length > 0 && !inventoryStale && (
                <select className="select" value={inventoryUrl} onChange={(e) => {
                  setInventoryUrl(e.target.value);
                  if (e.target.value) setPreview({ ...preview, image_url: e.target.value });
                }}>
                  <option value="">Select an inventory image</option>
                  {inventoryLookup.items.map((option) => <option key={option.url} value={option.url}>{option.label} · {option.url}</option>)}
                </select>
              )}
              {inventoryLookup.status === "ready" && inventoryLookup.total > 0 && (
                <span className="toolbar">
                  <button className="btn small" type="button" disabled={!inventoryLookup.offset} onClick={() => searchInventory(Math.max(0, inventoryLookup.offset - MEDIA_LOOKUP_PAGE_SIZE))}>Previous inventory</button>
                  <span>{inventoryLookup.offset + 1}–{Math.min(inventoryLookup.offset + MEDIA_LOOKUP_PAGE_SIZE, inventoryLookup.total)} of {inventoryLookup.total}</span>
                  <button className="btn small" type="button" disabled={inventoryLookup.offset + MEDIA_LOOKUP_PAGE_SIZE >= inventoryLookup.total} onClick={() => searchInventory(inventoryLookup.offset + MEDIA_LOOKUP_PAGE_SIZE)}>Next inventory</button>
                </span>
              )}
              <span className="toolbar">
                <button
                  className="btn primary"
                  disabled={!draftMutable || !!busy || !inventoryUrl}
                  onClick={() => resolve("inventory_match", {
                    selected_url: inventoryUrl,
                    values: presentationOnly,
                  })}
                >Use selected inventory image</button>
                <button
                  className="btn"
                  disabled={!draftMutable || !!busy || !preview.image_url}
                  onClick={() => resolve("manual_url", {
                    selected_url: preview.image_url,
                    values: presentationOnly,
                  })}
                >Advanced: use manual URL</button>
              </span>
            </div>
          )}
          {["unmatched", "unparseable"].includes(item.status) && (
            <div className="asset-resolution-stack">
              <label>Assign media to an existing promoted target
                <span className="toolbar compact-toolbar">
                  <input className="text" value={targetQuery} onChange={(e) => setTargetQuery(e.target.value)} placeholder="Name, RPO, or canonical ID" />
                  <button className="btn small" type="button" disabled={targetLookup.status === "loading"} onClick={() => searchTargets(0)}>Search targets</button>
                </span>
              </label>
              {targetLookup.status === "loading" && <div className="notice">Searching assignment targets…</div>}
              {targetLookup.status === "error" && (
                <div className="notice err">Target search failed: {targetLookup.error}{" "}
                  <button className="btn small" type="button" onClick={() => searchTargets(targetLookup.offset)}>Retry target search</button>
                </div>
              )}
              {targetsStale && <div className="notice warn">The target list changed. Search again before assigning media.</div>}
              {targetLookup.status === "ready" && !targetLookup.items.length && (
                <div className="empty">No workbook targets match this search.</div>
              )}
              {targetLookup.items.length > 0 && !targetsStale && (
                <div className="asset-target-results" role="radiogroup" aria-label="Assignment targets">
                  {targetLookup.items.map((target) => (
                    <button
                      className={targetItemId === target.item_id ? "selected" : ""}
                      type="button"
                      role="radio"
                      aria-checked={targetItemId === target.item_id}
                      key={target.item_id}
                      onClick={() => setTargetItemId(target.item_id)}
                    >
                      <strong>{target.label}</strong>
                      <span className="mono">{target.canonical_id}</span>
                      <small>{target.model_key} · {target.target_type} · {target.section_id}</small>
                    </button>
                  ))}
                </div>
              )}
              {targetLookup.status === "ready" && targetLookup.total > 0 && (
                <span className="toolbar">
                  <button className="btn small" type="button" disabled={!targetLookup.offset} onClick={() => searchTargets(Math.max(0, targetLookup.offset - TARGET_LOOKUP_PAGE_SIZE))}>Previous targets</button>
                  <span>{targetLookup.offset + 1}–{Math.min(targetLookup.offset + TARGET_LOOKUP_PAGE_SIZE, targetLookup.total)} of {targetLookup.total}</span>
                  <button className="btn small" type="button" disabled={targetLookup.offset + TARGET_LOOKUP_PAGE_SIZE >= targetLookup.total} onClick={() => searchTargets(targetLookup.offset + TARGET_LOOKUP_PAGE_SIZE)}>Next targets</button>
                </span>
              )}
              <span className="toolbar">
                <button
                  className="btn primary"
                  disabled={!draftMutable || !!busy || !targetItemId}
                  onClick={() => resolve("assign_media", {
                    target_item_id: targetItemId,
                    values: presentationOnly,
                  })}
                ><Link size={14} /> Assign to selected target</button>
                <button
                  className="btn"
                  disabled={!draftMutable || !!busy}
                  onClick={() => resolve("ignore", { values: {} })}
                ><Ban size={14} /> Ignore this exact media identity</button>
              </span>
            </div>
          )}
          {item.status === "stale_target" && (
            <button
              className="btn danger"
              disabled={!draftMutable || !!busy}
              onClick={() => resolve("deactivate", {
                values: { ...resolutionValues, active: false },
              })}
            ><Ban size={14} /> Add explicit stale-row deactivation</button>
          )}
          {item.status === "covered" && (
            <button className="btn primary" disabled={!draftMutable || !!busy} onClick={() => resolve("edit")}>
              <Save size={14} /> Save presentation edits to draft
            </button>
          )}
          {item.status === "wildcard_conflict" && (
            <div className="asset-resolution-stack">
              <div className="section-heading">Edit presentation</div>
              <p className="muted">Presentation fields do not decide which model owns the image URL.</p>
              <button className="btn" disabled={!draftMutable || !!busy} onClick={() => resolve("edit", { values: presentationOnly })}>
                <Save size={14} /> Edit presentation only
              </button>
              <div className="section-heading">Resolve ownership conflict</div>
              <dl className="identity-list">
                <dt>Shared wildcard</dt>
                <dd className="mono">{item.ownership_resolution?.shared_owner?.image_url || "none"}</dd>
                <dt>Current exact ownership</dt>
                <dd>{item.ownership_resolution?.current_exact_owner ? "present" : "none"}</dd>
                <dt>Affected models</dt>
                <dd>{item.ownership_resolution?.affected_models?.join(", ") || "unknown"}</dd>
              </dl>
              <button
                className="btn primary"
                disabled={!draftMutable || !!busy || !item.ownership_resolution?.exact_operation?.allowed}
                onClick={() => resolve("resolve_wildcard_exact", { values: presentationOnly })}
              >Create exact model ownership</button>
              <button
                className="btn"
                disabled={!draftMutable || !!busy || !item.ownership_resolution?.shared_operation?.allowed}
                onClick={() => resolve("resolve_wildcard_shared", { values: presentationOnly })}
              >Update shared wildcard ownership</button>
              {!item.ownership_resolution?.shared_operation?.allowed && (
                <div className="notice warn">
                  {item.ownership_resolution?.shared_operation?.blocked_reason || "Shared ownership cannot be resolved unambiguously."}
                </div>
              )}
            </div>
          )}
          {item.status === "ignored" && (
            <div className="notice ok">This exact media identity is ignored by durable manager evidence. Any inventory fingerprint change returns it to review.</div>
          )}
        </div>
      </div>
    </EditorShell>
  );
}
