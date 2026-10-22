import { test } from "node:test";
import assert from "node:assert/strict";
import { keys, safeGet, safeSet } from "../../web/js/lib/storage.js";

const throwing = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };

test("safeGet returns fallback when storage throws", () => {
  assert.equal(safeGet("k", "fb", throwing), "fb");
});

test("safeSet reports failure when storage throws", () => {
  assert.equal(safeSet("k", "v", throwing), false);
});

test("safeGet/safeSet round trip and missing key fallback", () => {
  const data = new Map();
  const store = { getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => data.set(k, String(v)) };
  assert.equal(safeGet("nhwc.nickname", "x", store), "x");
  assert.equal(safeSet("nhwc.nickname", "小王", store), true);
  assert.equal(safeGet("nhwc.nickname", "x", store), "小王");
});

test("safeGet without any storage returns fallback", () => {
  assert.equal(safeGet("k", "fb", undefined), "fb");
});

test("storage keys", () => {
  assert.equal(keys.nickname, "nhwc.nickname");
  assert.equal(keys.token("K922"), "nhwc.token.K922");
});
