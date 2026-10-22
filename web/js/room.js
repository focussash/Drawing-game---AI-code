// Room page bootstrap: identity, connection, and mounting the UI modules.
// Mode-specific UI is loaded on demand from modes/index.js.

import { mountBoard } from "./canvas/board.js";
import { keys, safeGet, safeSet } from "./lib/storage.js";
import { MODE_REDUCERS, MODE_VIEWS } from "./modes/index.js";
import { GameSocket, socketUrl } from "./net/socket.js";
import { createStore } from "./state/store.js";
import { mountChat } from "./ui/chat.js";
import { mountLobby } from "./ui/lobby.js";
import { askNickname } from "./ui/nickname.js";
import { mountStatus, showClosed } from "./ui/status.js";
import { showToast } from "./ui/toast.js";

const $ = (id) => document.getElementById(id);
const DEFAULT_NICKNAME_LENGTH = 12;
const NICKNAME_ERRORS = new Set(["need_nickname", "bad_nickname"]);

const code = (location.pathname.split("/")[2] ?? "").toUpperCase();
const store = createStore(MODE_REDUCERS);
const screen = $("screen");

let token = safeGet(keys.token(code));
let nickname = safeGet(keys.nickname, "");
let lastError = "";
let needNickname = false;
const messageHooks = []; // extra consumers of raw messages (the canvas)
const modeViews = {};
let activeView = null; // what the loaded mode view's mount() returned
let board = null;

const socket = new GameSocket({
  url: socketUrl(code),
  getHello: () => ({ type: "hello", token: token ?? undefined, nickname: nickname || undefined }),
  onMessage: handleMessage,
  onStatus: (status, reason) => {
    if (status === "closed" && reason === "rejected" && needNickname) {
      needNickname = false;
      promptThenConnect(lastError);
      return;
    }
    store.dispatch({ type: "_status", status, reason });
  },
});

function handleMessage(msg) {
  if (msg.type === "welcome") {
    token = msg.token;
    safeSet(keys.token(code), token);
  } else if (msg.type === "error") {
    lastError = msg.message;
    if (NICKNAME_ERRORS.has(msg.code)) {
      needNickname = true;
      token = null;
    } else if (store.getState().you) {
      showToast(msg.message);
    }
  }
  for (const hook of messageHooks) hook(msg);
  store.dispatch(msg);
}

async function promptThenConnect(message = "") {
  const maxLength = store.getState().limits?.max_nickname_length ?? DEFAULT_NICKNAME_LENGTH;
  nickname = await askNickname(screen, { initial: nickname, maxLength, message });
  safeSet(keys.nickname, nickname);
  socket.connect();
}

function applyLayout(state, prev) {
  if (state.state === prev?.state && state.mode === prev?.mode) return;
  const inGame = state.state === "game";
  document.body.classList.toggle("in-game", inGame);
  document.body.classList.toggle("in-lobby", !inGame);
  $("lobby").hidden = inGame;
  $("game").hidden = !inGame;
  if (inGame) loadModeView(state.mode);
}

function loadModeView(mode) {
  if (modeViews[mode] || !MODE_VIEWS[mode]) return;
  modeViews[mode] = MODE_VIEWS[mode]()
    .then((view) => {
      activeView = view.mount(shell);
      board.refresh(); // canDraw is known only now
    })
    .catch((err) => {
      console.error(err);
      delete modeViews[mode];
      showToast("游戏界面加载失败，请刷新页面");
    });
}

// What a mode view gets to work with.
const shell = {
  store,
  socket,
  regions: { topbar: $("topbar"), actions: $("actions"), scoreboard: $("scoreboard"), overlay: $("overlay"),
             tools: $("tools"), stage: $("stage"), canvas: $("canvas") },
  chat: null,
  onMessage: (fn) => messageHooks.push(fn),
};

function boot() {
  if (!/^[A-Z0-9]{4}$/.test(code)) {
    showClosed(screen, "not_found");
    return;
  }
  document.title = `你画我猜 ${code}`;
  mountStatus($("banner"), screen, store, { rejectedText: () => lastError });
  mountLobby($("lobby"), store, socket);
  shell.chat = mountChat($("chat-log"), $("chat-form"), $("chat-input"), store, socket);
  board = mountBoard({
    canvasEl: $("canvas"), toolsEl: $("tools"), store, socket, onMessage: shell.onMessage,
    canDraw: (state) => state.state === "game" && (activeView?.canDraw(state) ?? false),
  });
  store.subscribe(applyLayout);
  if (token) socket.connect();
  else promptThenConnect();
}

boot();
