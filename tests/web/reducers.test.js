import { test } from "node:test";
import assert from "node:assert/strict";
import { CHAT_LIMIT, applyMessage, initialState } from "../../web/js/state/reducers.js";
import { MODE_REDUCERS } from "../../web/js/modes/index.js";

const entry = (text) => ({ from: "p1", nickname: "a", text, kind: "chat", private: false });

function snapshot(overrides = {}) {
  return {
    room: "K922", state: "lobby", mode: "classic", host: "p1",
    players: [{ id: "p1", nickname: "a", online: true, host: true }],
    lobby: { specs: [], values: { rounds: 3 }, banks: ["默认"], last_results: null },
    drawing: { width: 1600, height: 1200, colors: ["#000000"], brush_sizes: [4], eraser_sizes: [16] },
    limits: { max_chat_length: 60, max_nickname_length: 12 },
    chat: [entry("hi")], canvas: [], game: null, ...overrides,
  };
}

const apply = (s, m, now = 0) => applyMessage(s, m, now, MODE_REDUCERS);
const welcome = (snap = snapshot()) => ({ type: "welcome", you: "p1", token: "t", snapshot: snap });

test("welcome loads the snapshot", () => {
  const s = apply(initialState(), welcome());
  assert.equal(s.you, "p1");
  assert.equal(s.token, "t");
  assert.equal(s.state, "lobby");
  assert.equal(s.room, "K922");
  assert.deepEqual(s.players.map((p) => p.id), ["p1"]);
  assert.deepEqual(s.chat.map((e) => e.text), ["hi"]);
  assert.equal(s.game, null);
});

test("messages before welcome are ignored", () => {
  const s0 = initialState();
  assert.equal(apply(s0, { type: "players", players: [] }), s0);
});

test("chat appends and is capped", () => {
  let s = apply(initialState(), welcome());
  for (let i = 0; i < CHAT_LIMIT + 5; i++) s = apply(s, { type: "chat", entry: entry(String(i)) });
  assert.equal(s.chat.length, CHAT_LIMIT);
  assert.equal(s.chat.at(-1).text, String(CHAT_LIMIT + 4));
});

test("players message updates host", () => {
  let s = apply(initialState(), welcome());
  s = apply(s, { type: "players", players: [{ id: "p1", nickname: "a", online: false, host: false }, { id: "p2", nickname: "b", online: true, host: true }] });
  assert.equal(s.host, "p2");
  assert.equal(s.players.length, 2);
});

test("lobby message replaces lobby and last results", () => {
  let s = apply(initialState(), welcome());
  s = apply(s, { type: "lobby", specs: [], values: { rounds: 5 }, banks: ["默认"], last_results: [{ id: "p1", nickname: "a", score: 3 }] });
  assert.equal(s.lobby.values.rounds, 5);
  assert.equal(s.lastResults[0].score, 3);
});

test("game_started then game_over", () => {
  let s = apply(initialState(), welcome());
  s = apply(s, { type: "game_started", mode: "classic" });
  assert.equal(s.state, "game");
  assert.ok(s.game);
  s = apply(s, { type: "game_over", results: [{ id: "p1", nickname: "a", score: 9 }] });
  assert.equal(s.state, "lobby");
  assert.equal(s.game, null);
  assert.equal(s.lastResults[0].score, 9);
});

test("welcome with a game snapshot computes the deadline", () => {
  const game = { phase: "drawing", round: 1, rounds: 3, drawer: "p2", remaining_ms: 5000, template: ["_"], extends_left: 0, scores: {}, correct: [] };
  const s = apply(initialState(), welcome(snapshot({ state: "game", game })), 1000);
  assert.equal(s.game.deadlineAt, 6000);
  assert.equal(s.game.phase, "drawing");
});

test("unknown message type returns the same state object", () => {
  const s = apply(initialState(), welcome());
  assert.equal(apply(s, { type: "nosuch" }), s);
});

test("status messages update connection status", () => {
  const s = apply(initialState(), { type: "_status", status: "reconnecting" });
  assert.equal(s.status, "reconnecting");
});
