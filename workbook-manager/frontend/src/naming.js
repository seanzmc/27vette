// Display-only naming helpers, mirroring backend app/naming.py.
const ACRONYMS = {
  lpo: "LPO", ovs: "OVS", lz: "LZ", lt: "LT", zr1: "ZR1", zr1x: "ZR1X",
  z06: "Z06", z51: "Z51", z52: "Z52", z07: "Z07", rpo: "RPO", id: "ID",
  gs: "GS", cf: "CF", api: "API", url: "URL", db: "DB",
};

export function humanize(raw) {
  if (!raw) return "";
  const txt = String(raw).replace(/([a-z0-9])([A-Z])/g, "$1 $2");
  return txt
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => ACRONYMS[w.toLowerCase()] || w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function displayId(canonicalId, prefixes = []) {
  const cid = String(canonicalId || "");
  for (const p of prefixes) {
    if (p && cid.startsWith(p) && cid.length > p.length) {
      return humanize(cid.slice(p.length));
    }
  }
  return humanize(cid);
}
