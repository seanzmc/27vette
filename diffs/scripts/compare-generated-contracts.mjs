#!/usr/bin/env node
import fs from "node:fs";
import assert from "node:assert/strict";

const IGNORED_KEYS = new Set(["generated_at", "sourceGeneratedAt", "generatedAt"]);

function normalize(value) {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      if (IGNORED_KEYS.has(key)) continue;
      out[key] = normalize(value[key]);
    }
    return out;
  }
  return value;
}

function readJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

const [beforePath, afterPath] = process.argv.slice(2);
if (!beforePath || !afterPath) {
  console.error("usage: node scripts/compare-generated-contracts.mjs before.json after.json");
  process.exit(2);
}

const before = normalize(readJson(beforePath));
const after = normalize(readJson(afterPath));

try {
  assert.deepStrictEqual(after, before);
  console.log(`contracts match: ${beforePath} ${afterPath}`);
} catch (error) {
  console.error(`contracts differ: ${beforePath} ${afterPath}`);
  throw error;
}
