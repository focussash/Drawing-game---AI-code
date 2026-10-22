// Connection status: a "reconnecting" banner, and a full screen when the
// connection ended for good (kicked, room gone, opened elsewhere...).

import { h } from "../lib/dom.js";

const CLOSED_TEXT = {
  replaced: ["已在其他页面打开", "这个房间在另一个标签页或设备上打开了，这里就先断开。"],
  kicked: ["你被房主移出了房间", "如果是误会，让房主发个新房间的链接吧。"],
  not_found: ["房间不存在", "可能是房间码打错了，或者房间太久没人用已经关闭了。"],
};

export function mountStatus(bannerEl, screenEl, store, { rejectedText }) {
  store.subscribe((state, prev) => {
    if (state.status === prev.status && state.closedReason === prev.closedReason) return;
    bannerEl.hidden = state.status !== "reconnecting";
    bannerEl.textContent = "连接断开了，正在重新连接…";
    if (state.status === "closed") showClosed(screenEl, state.closedReason, rejectedText());
  });
}

export function showClosed(screenEl, reason, rejectedText) {
  const [title, body] = CLOSED_TEXT[reason] ?? ["无法进入房间", rejectedText || "连接已断开。"];
  screenEl.replaceChildren(
    h("div", { class: "screen-card" },
      h("h2", {}, title),
      h("p", {}, body),
      h("a", { class: "btn primary", href: "/", style: "text-align:center;text-decoration:none;line-height:28px" }, "回到首页"),
    ),
  );
  screenEl.hidden = false;
}
