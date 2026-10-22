import { test } from "node:test";
import assert from "node:assert/strict";
import { reduceClassic } from "../../web/js/modes/classic/reducer.js";
import { reasonText, secondsLeft, templateText } from "../../web/js/modes/classic/format.js";

test("phase sets deadline from remaining_ms", () => {
  const g = reduceClassic(null, { type: "phase", phase: "drawing", round: 1, rounds: 3, drawer: "p1", remaining_ms: 80000, template: ["_", "_"] }, 500);
  assert.equal(g.deadlineAt, 80500);
  assert.deepEqual(g.template, ["_", "_"]);
});

test("new choosing phase clears the previous turn", () => {
  let g = reduceClassic(null, { type: "word", word: "长颈鹿" }, 0);
  g = reduceClassic(g, { type: "turn_result", word: "长颈鹿", reason: "time", drawer: "p1", deltas: {} }, 0);
  g = reduceClassic(g, { type: "scores", scores: { p1: 1 }, correct: ["p2"] }, 0);
  g = reduceClassic(g, { type: "choices", words: ["a"] }, 0);
  g = reduceClassic(g, { type: "phase", phase: "choosing", round: 1, rounds: 3, drawer: "p2", remaining_ms: 15000, template: null }, 0);
  assert.equal(g.word, null);
  assert.equal(g.turn_result, null);
  assert.equal(g.choices, null);
  assert.deepEqual(g.correct, []);
  assert.deepEqual(g.scores, { p1: 1 });
});

test("hint, timer and scores", () => {
  let g = reduceClassic(null, { type: "hint", template: ["_", "颈", "_"] }, 0);
  assert.deepEqual(g.template, ["_", "颈", "_"]);
  g = reduceClassic(g, { type: "timer", remaining_ms: 20000, extends_left: 2 }, 100);
  assert.equal(g.deadlineAt, 20100);
  assert.equal(g.extends_left, 2);
  g = reduceClassic(g, { type: "scores", scores: { p2: 88 }, correct: ["p2"] }, 0);
  assert.deepEqual(g.correct, ["p2"]);
});

test("unknown type returns the same game object", () => {
  const g = reduceClassic(null, { type: "hint", template: [] }, 0);
  assert.equal(reduceClassic(g, { type: "nosuch" }, 0), g);
});

test("templateText", () => {
  assert.equal(templateText(["_", "颈", "_"]), "_ 颈 _");
  assert.equal(templateText(["_", " ", "_"]), "_   _");
  assert.equal(templateText(null), "？");
});

test("secondsLeft rounds up and floors at zero", () => {
  assert.equal(secondsLeft(1000 + 1500, 1000), 2);
  assert.equal(secondsLeft(1000, 5000), 0);
  assert.equal(secondsLeft(null, 0), 0);
});

test("reasonText", () => {
  assert.equal(reasonText("time"), "时间到");
  assert.equal(reasonText("all_correct"), "全部猜对");
  assert.equal(reasonText("skipped"), "已跳过");
  assert.equal(reasonText("drawer_left"), "画手离开了");
});
