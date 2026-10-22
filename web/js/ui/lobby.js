// Lobby: room code and share link, players, the host's settings (form built
// from the mode's setting specs), start button and the last game's ranking.

import { h } from "../lib/dom.js";
import { renderPlayers } from "./players.js";
import { showToast } from "./toast.js";

export function mountLobby(el, store, socket) {
  const render = (state) => {
    if (!state.lobby) return;
    const parts = [
      renderShare(state),
      section(`玩家（${state.players.length}）`, renderPlayers(state, socket)),
      state.lastResults ? section("上一局排名", renderResults(state.lastResults)) : null,
      section("这一局的设置", renderSettings(state, socket)),
      renderStart(state, socket),
    ];
    el.replaceChildren(...parts.filter(Boolean));
  };
  store.subscribe((state, prev) => {
    if (state.lobby !== prev.lobby || state.players !== prev.players || state.host !== prev.host
        || state.lastResults !== prev.lastResults || state.you !== prev.you) {
      render(state);
    }
  });
}

function section(title, body) {
  return h("div", {}, h("h2", {}, title), body);
}

function renderShare(state) {
  const link = location.href;
  const linkBox = h("input", { class: "field share-link", readonly: true, value: link, hidden: true });
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      showToast("链接已复制，发到群里吧");
    } catch {
      // Clipboard needs https; on a LAN address show the link so it can be copied by hand.
      linkBox.hidden = false;
      linkBox.select();
    }
  };
  return h("div", {},
    h("div", { class: "room-code", "aria-label": `房间码 ${state.room}` }, state.room),
    h("div", { class: "share-row muted" },
      "把这个页面的链接发到群里，大家点开就能进",
      h("button", { class: "btn quiet small", onclick: copy }, "复制链接"),
    ),
    linkBox,
  );
}

function renderResults(results) {
  return h("ol", { class: "results" },
    results.map((r, i) => h("li", {},
      h("span", { class: "name" }, `${i + 1}. ${r.nickname}`),
      h("span", { class: "score" }, `${r.score} 分`),
    )),
  );
}

function renderSettings(state, socket) {
  const editable = state.you === state.host;
  const { specs, values, banks } = state.lobby;
  const send = (key, value) => socket.send("settings", { values: { [key]: value } });
  const rows = specs.flatMap((spec) => {
    const value = values[spec.key];
    let control;
    if (spec.kind === "int") {
      control = h("span", { class: "stepper" },
        h("button", { class: "btn", disabled: !editable || value <= spec.min, "aria-label": `${spec.label}减少`,
                      onclick: () => send(spec.key, value - 1) }, "−"),
        h("span", { class: "value" }, value),
        h("button", { class: "btn", disabled: !editable || value >= spec.max, "aria-label": `${spec.label}增加`,
                      onclick: () => send(spec.key, value + 1) }, "+"),
      );
    } else if (spec.kind === "bool") {
      control = h("button", { class: "chip", "aria-pressed": String(value), disabled: !editable,
                              onclick: () => send(spec.key, !value) }, value ? "开" : "关");
    } else if (spec.kind === "banks") {
      control = h("span", { class: "chips" },
        banks.length === 0 ? h("span", { class: "muted" }, "words 文件夹里还没有词库") : null,
        banks.map((bank) => {
          const on = value.includes(bank);
          const next = on ? value.filter((b) => b !== bank) : [...value, bank];
          return h("button", { class: "chip", "aria-pressed": String(on), disabled: !editable || (on && value.length === 1),
                               onclick: () => send(spec.key, next) }, bank);
        }),
      );
    } else {
      return [];
    }
    return [h("span", {}, spec.label), control];
  });
  return h("div", { class: "settings" }, rows);
}

function renderStart(state, socket) {
  if (state.you !== state.host) {
    const host = state.players.find((p) => p.host);
    return h("p", { class: "muted" }, `等房主${host ? `「${host.nickname}」` : ""}开始游戏…`);
  }
  return h("div", { class: "start-row" },
    h("button", { class: "btn primary", onclick: () => socket.send("start") }, "开始游戏"),
  );
}
