/* =========================================================================
 * 27vette — Layered Build Visualizer (v1)
 * -------------------------------------------------------------------------
 * Drop-in, dependency-free. Load this AFTER app.js with a plain <script>:
 *
 *     <script src="app.js"></script>
 *     <script src="visualizer.js"></script>
 *
 * It reads the SAME globals app.js already defines (state, optionsById,
 * choiceForCurrentVariant, currentVariant). No build step, no framework.
 *
 * DATA CONTRACT (emit these from your Python pipeline onto choice rows,
 * exactly like you already emit image_url):
 *   layer_src      string  filename or path of the web-sized PNG/WebP layer
 *                          e.g. "wheels/q8x.webp"  (body+color rows hold the
 *                          baked full-car art, e.g. "body/coupe_gba.webp")
 *   layer_z        number  stacking priority, low = behind. Optional; if
 *                          omitted, falls back to DEFAULT_Z by section_id.
 *   layer_src_full string  OPTIONAL path to the 2500px master, used only for
 *                          the downloaded image. Falls back to layer_src.
 *
 * Anything WITHOUT a layer_src is simply ignored — so you can ship art a
 * few sections at a time and the rest of the form is unaffected.
 * ========================================================================= */

(function () {
  "use strict";

  const VIS = {
    mountId: "vetteStage",        // <div id="vetteStage"></div> — place it anywhere
    assetBase: "assets/vehicle/", // prefixed to layer_src unless it's already a URL/abs path
    aspect: 2500 / 1807,          // source render aspect; layers scale to fit this box
    exportWidth: 2500,            // flattened download size
    exportHeight: 1807,
    fadeMs: 140,
  };

  // Fallback stacking order when a row has no explicit layer_z.
  // Lower number = painted first = sits behind. Tune freely.
  const DEFAULT_Z = {
    background: 0,
    vehicle: 10,           // body + color base layer
    exterior_paint: 10,    // (paint rows carry the body art on most setups)
    exterior_appearance: 20,
    stripes: 30,
    wheels_brakes: 40,     // calipers should be a lower z than the wheel itself
    performance_mechanical: 45,
    accessories: 50,
    glass: 90,
  };

  // ---- helpers that lean on app.js globals (guarded so we never crash it) ----
  function rowFor(optionId) {
    if (typeof choiceForCurrentVariant === "function") {
      const r = choiceForCurrentVariant(optionId);
      if (r) return r;
    }
    if (typeof optionsById !== "undefined" && optionsById.get) {
      return optionsById.get(optionId) || null;
    }
    return null;
  }

  function resolveSrc(src) {
    if (!src) return "";
    if (/^(https?:)?\/\//.test(src) || src.startsWith("/")) return src;
    return VIS.assetBase + src;
  }

  function zFor(row) {
    if (row.layer_z !== undefined && row.layer_z !== "" && row.layer_z !== null) {
      return Number(row.layer_z);
    }
    return DEFAULT_Z[row.section_id] ?? 25;
  }

  // Build the desired stack from whatever is currently selected.
  function desiredLayers() {
    if (typeof state === "undefined" || !state.selected) return [];
    const out = [];
    for (const optionId of state.selected) {
      const row = rowFor(optionId);
      if (!row || !row.layer_src) continue;
      out.push({
        key: optionId,
        z: zFor(row),
        src: resolveSrc(row.layer_src),
        fullSrc: resolveSrc(row.layer_src_full || row.layer_src),
        alt: (row.rpo ? row.rpo + " " : "") + (row.label || ""),
      });
    }
    out.sort((a, b) => a.z - b.z);
    return out;
  }

  // ---- mount + styles ----
  let stage = null;
  const mounted = new Map(); // option_id -> <img>
  const imgCache = new Map(); // src -> HTMLImageElement (warm cache)

  function ensureStyles() {
    if (document.getElementById("vette-vis-styles")) return;
    const css = `
      #${VIS.mountId}{position:relative;width:100%;aspect-ratio:${VIS.aspect};
        overflow:hidden;background:transparent;}
      #${VIS.mountId} .vette-layer{position:absolute;inset:0;width:100%;height:100%;
        object-fit:contain;opacity:0;transition:opacity ${VIS.fadeMs}ms ease;
        pointer-events:none;}
      #${VIS.mountId} .vette-layer.is-on{opacity:1;}
    `;
    const el = document.createElement("style");
    el.id = "vette-vis-styles";
    el.textContent = css;
    document.head.appendChild(el);
  }

  function ensureStage() {
    if (stage) return stage;
    stage = document.getElementById(VIS.mountId);
    if (!stage) {
      stage = document.createElement("div");
      stage.id = VIS.mountId;
      const host = document.querySelector(".app-shell") || document.body;
      host.prepend(stage);
    }
    ensureStyles();
    return stage;
  }

  function preload(src) {
    if (!src || imgCache.has(src)) return imgCache.get(src);
    const img = new Image();
    img.decoding = "async";
    img.src = src;
    imgCache.set(src, img);
    return img;
  }

  // ---- the render: diff against what's on screen, no flicker ----
  function renderVisualizer() {
    const host = ensureStage();
    const desired = desiredLayers();
    const wanted = new Set(desired.map((l) => l.key));

    // remove layers no longer selected
    for (const [key, img] of mounted) {
      if (!wanted.has(key)) {
        img.classList.remove("is-on");
        const node = img;
        setTimeout(() => node.remove(), VIS.fadeMs);
        mounted.delete(key);
      }
    }

    // add / update
    for (const layer of desired) {
      let img = mounted.get(layer.key);
      if (!img) {
        img = document.createElement("img");
        img.className = "vette-layer";
        img.alt = layer.alt;
        img.addEventListener("load", () => img.classList.add("is-on"), { once: true });
        host.appendChild(img);
        mounted.set(layer.key, img);
      }
      if (img.getAttribute("src") !== layer.src) {
        img.classList.remove("is-on");
        img.src = layer.src;
        if (img.complete) img.classList.add("is-on");
      }
      img.style.zIndex = String(layer.z);
      preload(layer.fullSrc); // warm the master for export
    }
  }

  // ---- the "compiler": flatten the stack into one downloadable PNG ----
  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "anonymous"; // needed if assets are served cross-origin
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Failed to load " + src));
      img.src = src;
    });
  }

  async function exportBuildImage(filename = "corvette-build.png") {
    const layers = desiredLayers(); // already z-sorted
    if (!layers.length) return null;
    const canvas = document.createElement("canvas");
    canvas.width = VIS.exportWidth;
    canvas.height = VIS.exportHeight;
    const ctx = canvas.getContext("2d");
    for (const layer of layers) {
      try {
        const img = await loadImage(layer.fullSrc);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      } catch (e) {
        console.warn("[visualizer]", e.message);
      }
    }
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        if (!blob) return resolve(null);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        resolve(blob);
      }, "image/png");
    });
  }

  // ---- auto-hook: re-render whenever app.js re-renders (zero edits to app.js)
  // app.js's render() runs on every selection change; we wrap it so the
  // visualizer stays in sync. If you'd rather be explicit, delete this block
  // and add `renderVisualizer();` at the end of render() in app.js instead.
  try {
    if (typeof render === "function") {
      const _render = render;
      // eslint-disable-next-line no-global-assign
      render = function () {
        const out = _render.apply(this, arguments);
        try { renderVisualizer(); } catch (e) { console.warn("[visualizer]", e); }
        return out;
      };
    }
  } catch (e) {
    console.warn("[visualizer] auto-hook unavailable; call renderVisualizer() from render()", e);
  }

  // expose for manual calls + the export button
  window.renderVisualizer = renderVisualizer;
  window.exportBuildImage = exportBuildImage;
  window.VETTE_VIS = VIS;

  // first paint
  if (document.readyState !== "loading") renderVisualizer();
  else document.addEventListener("DOMContentLoaded", renderVisualizer);
})();
