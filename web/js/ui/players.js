// The lobby's player list: who is here, who is host, and (for the host) kick buttons.

import { h } from "../lib/dom.js";

export function renderPlayers(state, socket) {
  const isHost = state.you === state.host;
  return h("ul", { class: "plist" },
    state.players.map((p) =>
      h("li", { class: p.online ? "" : "offline" },
        h("span", {},
          p.nickname,
          p.host ? h("span", { class: "tag" }, "房主") : null,
          p.id === state.you ? h("span", { class: "tag" }, "你") : null,
          p.online ? null : h("span", { class: "muted" }, "（掉线）"),
        ),
        isHost && p.id !== state.you
          ? h("button", {
              class: "btn quiet small",
              onclick: () => {
                if (confirm(`把「${p.nickname}」移出房间？`)) socket.send("kick", { player_id: p.id });
              },
            }, "移出")
          : null,
      ),
    ),
  );
}
