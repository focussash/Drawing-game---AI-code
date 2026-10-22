// A dismissible hint shown inside WeChat's built-in browser, which tends to
// drop connections and block unknown links: suggest opening the page in the
// phone's real browser instead.

import { h } from "../lib/dom.js";
import { keys, safeGet, safeSet } from "../lib/storage.js";

export function isWeChat(ua = globalThis.navigator?.userAgent) {
  return /MicroMessenger/i.test(ua ?? "");
}

export function mountWeChatHint(el) {
  if (!isWeChat() || safeGet(keys.wechatHintDismissed)) return;
  el.replaceChildren(
    h("span", {}, "在微信里打开容易断线。建议点右上角「···」，选「在浏览器打开」。"),
    h("button", {
      class: "btn quiet small",
      onclick: () => {
        el.hidden = true;
        safeSet(keys.wechatHintDismissed, "1");
      },
    }, "知道了"),
  );
  el.hidden = false;
}
