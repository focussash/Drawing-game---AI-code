import { test } from "node:test";
import assert from "node:assert/strict";
import {
  canDraw, chatPlaceholder, deltaRows, hintCells, scoreRows,
} from "../../web/js/modes/classic/selectors.js";

const players = [
  { id: "p1", nickname: "小王", online: true, host: true },
  { id: "p2", nickname: "阿杰", online: true, host: false },
  { id: "p3", nickname: "小美", online: false, host: false },
];

function state(you, game) {
  return {
    you, players, state: "game", lobby: { values: { extend_seconds: 10 } },
    game: { phase: "drawing", round: 1, rounds: 3, drawer: "p1", deadlineAt: 0, template: ["_", "_", "_"],
            word: null, choices: null, extends_left: 3, scores: {}, correct: [], turn_result: null, ...game },
  };
}

test("canDraw only for the drawer while drawing", () => {
  assert.equal(canDraw(state("p1", {})), true);
  assert.equal(canDraw(state("p2", {})), false);
  assert.equal(canDraw(state("p1", { phase: "choosing" })), false);
  assert.equal(canDraw({ ...state("p1", {}), state: "lobby" }), false);
});

test("guesser sees blanks, revealed characters and gaps", () => {
  const cells = hintCells(state("p2", { template: ["_", "颈", " ", "_"] }));
  assert.deepEqual(cells.map((c) => [c.kind, c.char]), [["blank", ""], ["revealed", "颈"], ["gap", ""], ["blank", ""]]);
  assert.ok(cells.every((c) => !c.tappable));
});

test("guesser without the length hint sees nothing", () => {
  assert.equal(hintCells(state("p2", { template: null })), null);
});

test("drawer sees the word and may tap unrevealed characters", () => {
  const cells = hintCells(state("p1", { word: "长颈鹿", template: ["_", "颈", "_"] }));
  assert.deepEqual(cells.map((c) => [c.kind, c.char, c.tappable]),
    [["shown", "长", true], ["revealed", "颈", false], ["shown", "鹿", true]]);
});

test("drawer cannot reveal the last hidden character", () => {
  const cells = hintCells(state("p1", { word: "长颈鹿", template: ["长", "颈", "_"] }));
  assert.ok(cells.every((c) => !c.tappable));
});

test("drawer with length hint off can still reveal", () => {
  const cells = hintCells(state("p1", { word: "猫咪", template: null }));
  assert.deepEqual(cells.map((c) => c.tappable), [true, true]);
});

test("a correct guesser sees the whole word but cannot reveal", () => {
  const cells = hintCells(state("p2", { word: "长颈鹿", correct: ["p2"] }));
  assert.deepEqual(cells.map((c) => [c.kind, c.char, c.tappable]),
    [["shown", "长", false], ["shown", "颈", false], ["shown", "鹿", false]]);
});

test("turn end shows the answer to everyone; choosing shows nothing", () => {
  const end = hintCells(state("p3", { phase: "turn_end", word: "熊猫", template: null }));
  assert.deepEqual(end.map((c) => c.char), ["熊", "猫"]);
  assert.equal(hintCells(state("p2", { phase: "choosing" })), null);
});

test("chat placeholder depends on who knows the answer", () => {
  assert.equal(chatPlaceholder(state("p1", {})), "只有猜对的人能看到");
  assert.equal(chatPlaceholder(state("p2", { correct: ["p2"] })), "只有画手和猜对的人能看到");
  assert.equal(chatPlaceholder(state("p2", {})), "输入你的猜测");
  assert.equal(chatPlaceholder(state("p2", { phase: "turn_end" })), "说点什么");
});

test("scoreRows keeps join order and marks drawer, correct and offline", () => {
  const rows = scoreRows(state("p2", { scores: { p1: 25, p2: 88 }, correct: ["p2"] }));
  assert.deepEqual(rows.map((r) => [r.nickname, r.score, r.drawer, r.correct, r.online]), [
    ["小王", 25, true, false, true], ["阿杰", 88, false, true, true], ["小美", 0, false, false, false],
  ]);
});

test("deltaRows sorts this turn's points with nicknames", () => {
  const s = state("p2", { phase: "turn_end", turn_result: { word: "熊猫", reason: "time", drawer: "p1", deltas: { p1: 25, p2: 88 } } });
  assert.deepEqual(deltaRows(s), [{ nickname: "阿杰", points: 88 }, { nickname: "小王", points: 25 }]);
});
