import { test } from "node:test";
import assert from "node:assert/strict";
import { socketUrl } from "../../web/js/net/socket.js";
import { createStore } from "../../web/js/state/store.js";
import { MODE_REDUCERS } from "../../web/js/modes/index.js";

test("socketUrl follows the page scheme and host", () => {
  assert.equal(socketUrl("K922", { protocol: "http:", host: "192.168.1.5:8000" }), "ws://192.168.1.5:8000/ws/K922");
  assert.equal(socketUrl("K922", { protocol: "https:", host: "game.example.com" }), "wss://game.example.com/ws/K922");
});

test("store notifies with previous state, and stays quiet on no-ops", () => {
  const store = createStore(MODE_REDUCERS, () => 0);
  const calls = [];
  store.subscribe((state, prev) => calls.push([state.status, prev.status]));
  store.dispatch({ type: "_status", status: "reconnecting" });
  store.dispatch({ type: "players", players: [] }); // ignored before welcome
  assert.deepEqual(calls, [["reconnecting", "connecting"]]);
  assert.equal(store.getState().status, "reconnecting");
});
