// Classic mode screens: round and countdown, the 田字格 hint, word choices,
// turn results, drawer/host buttons and the scoreboard.
// Contract with room.js: mount(shell) → { canDraw(state) }.

import { h } from "../../lib/dom.js";
import { reasonText, secondsLeft } from "./format.js";
import { canDraw, chatPlaceholder, deltaRows, hintCells, isDrawer, nicknameOf, scoreRows } from "./selectors.js";

const TICK_MS = 250;
const URGENT_SECONDS = 10;
const STYLESHEET = "/static/css/classic.css";
const DEFAULT_EXTEND_SECONDS = 10;

export function mount(shell) {
  ensureStylesheet();
  const { store, socket, regions } = shell;
  const act = (name, data = {}) => socket.send("action", { name, data });

  const roundEl = h("span", { class: "round" });
  const hintEl = h("div", { class: "tian", "aria-live": "polite" });
  const timerEl = h("span", { class: "timer", "aria-label": "剩余秒数" });
  regions.topbar.replaceChildren(roundEl, hintEl, timerEl);

  function render(state, prev) {
    if (state.state !== "game" || !state.game) return;
    const changed = !prev || state.game !== prev.game || state.players !== prev.players
      || state.you !== prev.you || state.host !== prev.host;
    if (!changed) return;
    const g = state.game;
    roundEl.textContent = g.rounds ? `第 ${g.round}/${g.rounds} 圈` : "";
    renderHint(hintEl, state, act);
    renderOverlay(regions.overlay, state, act);
    renderActions(regions.actions, state, act);
    renderScoreboard(regions.scoreboard, state);
    shell.chat?.setPlaceholder(chatPlaceholder(state));
    tick();
  }

  let shownSeconds = null;
  function tick() {
    const g = store.getState().game;
    const secs = g && g.phase ? secondsLeft(g.deadlineAt, Date.now()) : null;
    if (secs === shownSeconds) return;
    shownSeconds = secs;
    timerEl.textContent = secs ?? "";
    timerEl.classList.toggle("urgent", g?.phase === "drawing" && secs !== null && secs <= URGENT_SECONDS);
  }

  setInterval(tick, TICK_MS);
  store.subscribe(render);
  render(store.getState(), null);
  return { canDraw };
}

function ensureStylesheet() {
  if (document.querySelector(`link[href="${STYLESHEET}"]`)) return;
  document.head.append(h("link", { rel: "stylesheet", href: STYLESHEET }));
}

function renderHint(el, state, act) {
  const g = state.game;
  const cells = hintCells(state);
  if (!cells) {
    let text = "";
    if (g.phase === "choosing") text = isDrawer(state) ? "选一个词" : "选词中…";
    else if (g.phase === "drawing") text = "不提示字数";
    else if (g.phase === "turn_end") text = "本轮跳过";
    el.replaceChildren(h("span", { class: "hint-text" }, text));
    return;
  }
  el.replaceChildren(...cells.map((c) => {
    if (c.kind === "gap") return h("span", { class: "gap" });
    if (!c.tappable) return h("span", { class: `cell ${c.kind}` }, c.char);
    return h("button", {
      class: `cell ${c.kind} tappable`,
      "aria-label": `揭示「${c.char}」`,
      onclick: () => {
        if (confirm(`揭示「${c.char}」？之后猜对的人和你的得分都会打折`)) act("reveal", { index: c.index });
      },
    }, c.char);
  }));
}

function renderOverlay(el, state, act) {
  const g = state.game;
  let card = null;
  if (g.phase === "choosing" && isDrawer(state) && g.choices) {
    card = h("div", { class: "pick" },
      h("p", {}, "轮到你画了，选一个词"),
      h("div", { class: "pick-words" },
        g.choices.map((word, index) => h("button", { class: "btn pick-word", onclick: () => act("choose", { index }) }, word))),
    );
  } else if (g.phase === "choosing") {
    card = h("p", { class: "waiting" }, `「${nicknameOf(state, g.drawer)}」正在选词…`);
  } else if (g.phase === "turn_end" && g.turn_result) {
    const word = g.turn_result.word;
    card = h("div", { class: "result" },
      h("p", { class: "muted" }, reasonText(g.turn_result.reason)),
      word ? h("p", { class: "answer" }, "答案是", h("strong", {}, word)) : h("p", { class: "answer" }, "本轮跳过"),
      h("ul", { class: "deltas" },
        deltaRows(state).map((r) => h("li", {}, h("span", {}, r.nickname), h("span", { class: "plus" }, `+${r.points}`)))),
    );
  }
  el.hidden = !card;
  el.replaceChildren(...(card ? [card] : []));
}

function renderActions(el, state, act) {
  const g = state.game;
  const buttons = [];
  if (g.phase === "drawing" && isDrawer(state)) {
    const seconds = state.lobby?.values?.extend_seconds ?? DEFAULT_EXTEND_SECONDS;
    buttons.push(h("button", { class: "btn", disabled: g.extends_left <= 0, onclick: () => act("extend") },
      g.extends_left > 0 ? `+${seconds} 秒（还剩 ${g.extends_left} 次）` : "加时次数用完了"));
  }
  if (state.you === state.host && (g.phase === "choosing" || g.phase === "drawing")) {
    buttons.push(h("button", {
      class: "btn quiet",
      onclick: () => confirm("跳过这一轮？") && act("skip"),
    }, "跳过这一轮"));
  }
  el.replaceChildren(...buttons);
}

function renderScoreboard(el, state) {
  el.replaceChildren(...scoreRows(state).map((r) => {
    const classes = ["pl"];
    if (r.drawer) classes.push("drawer");
    if (r.correct) classes.push("got");
    if (!r.online) classes.push("offline");
    if (r.you) classes.push("you");
    return h("div", { class: classes.join(" ") }, h("b", {}, r.nickname), h("span", {}, r.score));
  }));
}
