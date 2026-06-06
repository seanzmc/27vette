// =========================================================================
// export-layers.jsx  —  Photoshop layer -> aligned PNG exporter for 27vette
// -------------------------------------------------------------------------
// Run from Photoshop: File > Scripts > Browse... and pick this file.
//
// What it does:
//   Exports EACH top-level layer (or group) of the open document as its own
//   PNG-24 with transparency, at the FULL canvas size (no trimming, no
//   cropping). Because nothing is trimmed, every export shares the same
//   2500x1807 registration and stacks pixel-perfect in the web app.
//
// How to set up your PSD:
//   - One component per top-level layer OR group.
//   - Name each top-level layer/group EXACTLY the value you'll put in the
//     `layer_src` column, minus the extension. e.g. a group named  q8x
//     exports  q8x.png  -> later you reference  "wheels/q8x.webp".
//   - The body+color base is just another layer/group, e.g.  coupe_gba.
//
// After export: batch-convert the PNGs to WebP (~1400-1600px wide) for the
// web set, and keep the 2500px PNGs as masters for the download/export path.
// =========================================================================

#target photoshop

(function () {
  if (!app.documents.length) {
    alert("Open your layered PSD first.");
    return;
  }

  var doc = app.activeDocument;
  var folder = Folder.selectDialog("Choose a folder to export the layer PNGs into");
  if (!folder) return;

  var top = doc.layers;
  var n = top.length;

  // remember current visibility so we can restore it afterward
  var savedVisibility = [];
  var i;
  for (i = 0; i < n; i++) savedVisibility[i] = top[i].visible;

  // hide everything
  for (i = 0; i < n; i++) top[i].visible = false;

  // PNG-24 with full alpha, exported at canvas size (SaveForWeb never trims)
  var opts = new ExportOptionsSaveForWeb();
  opts.format = SaveDocumentType.PNG;
  opts.PNG8 = false;
  opts.transparency = true;
  opts.interlaced = false;

  var exported = 0;
  for (i = 0; i < n; i++) {
    top[i].visible = true;

    var safeName = top[i].name.replace(/[^A-Za-z0-9_\-]/g, "_");
    var file = new File(folder.fsName + "/" + safeName + ".png");

    try {
      doc.exportDocument(file, ExportType.SAVEFORWEB, opts);
      exported++;
    } catch (e) {
      // keep going even if one layer fails
    }

    top[i].visible = false;
  }

  // restore original visibility
  for (i = 0; i < n; i++) top[i].visible = savedVisibility[i];

  alert("Exported " + exported + " of " + n + " layers at full canvas size to:\n" + folder.fsName);
})();
