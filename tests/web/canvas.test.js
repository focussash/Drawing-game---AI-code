import { test } from "node:test";
import assert from "node:assert/strict";
import { fitBox, toLogical } from "../../web/js/canvas/geometry.js";
import { MAX_POINTS_PER_MESSAGE, StrokeBatcher } from "../../web/js/canvas/batcher.js";

const rect = { left: 100, top: 50, width: 400, height: 300 };

test("toLogical maps the canvas corners to the logical space", () => {
  assert.deepEqual(toLogical(100, 50, rect, 1600, 1200), [0, 0]);
  assert.deepEqual(toLogical(500, 350, rect, 1600, 1200), [1600, 1200]);
  assert.deepEqual(toLogical(300, 200, rect, 1600, 1200), [800, 600]);
});

test("toLogical clamps points outside the canvas", () => {
  assert.deepEqual(toLogical(0, 0, rect, 1600, 1200), [0, 0]);
  assert.deepEqual(toLogical(900, 900, rect, 1600, 1200), [1600, 1200]);
});

test("fitBox finds the largest 4:3 box", () => {
  assert.deepEqual(fitBox(400, 800), { w: 400, h: 300 });
  assert.deepEqual(fitBox(1000, 300), { w: 400, h: 300 });
});

function recorder() {
  const sent = [];
  return { sent, send: (type, data) => sent.push([type, data]) };
}

test("begin sends stroke_begin immediately with increasing ids", () => {
  const r = recorder();
  const b = new StrokeBatcher(r.send);
  b.begin("brush", "#000000", 8, 10, 20);
  assert.deepEqual(r.sent, [["stroke_begin", { id: 1, tool: "brush", color: "#000000", size: 8, x: 10, y: 20 }]]);
  b.end();
  b.begin("eraser", "#ffffff", 16, 0, 0);
  assert.equal(r.sent.at(-1)[1].id, 2);
});

test("moves are buffered, duplicates dropped, and flushed as flat points", () => {
  const r = recorder();
  const b = new StrokeBatcher(r.send);
  b.begin("brush", "#000000", 8, 10, 20);
  b.move(10, 20);
  b.move(11, 21);
  b.move(11, 21);
  b.move(12, 22);
  assert.equal(r.sent.length, 1);
  b.flush();
  assert.deepEqual(r.sent[1], ["stroke_points", { id: 1, pts: [11, 21, 12, 22] }]);
  b.flush();
  assert.equal(r.sent.length, 2);
});

test("long strokes are split to respect the message limit", () => {
  const r = recorder();
  const b = new StrokeBatcher(r.send);
  b.begin("brush", "#000000", 8, 0, 0);
  for (let i = 1; i <= 250; i++) b.move(i, i);
  b.end();
  const chunks = r.sent.filter(([type]) => type === "stroke_points").map(([, d]) => d.pts.length);
  assert.deepEqual(chunks, [MAX_POINTS_PER_MESSAGE, 500 - MAX_POINTS_PER_MESSAGE]);
});

test("move without begin does nothing", () => {
  const r = recorder();
  const b = new StrokeBatcher(r.send);
  b.move(1, 1);
  b.flush();
  assert.equal(r.sent.length, 0);
});
