// Full-screen nickname prompt. Resolves with the trimmed nickname.

import { h } from "../lib/dom.js";

export function askNickname(screenEl, { initial = "", maxLength = 12, message = "" } = {}) {
  return new Promise((resolve) => {
    const input = h("input", {
      class: "field", maxlength: maxLength, value: initial, placeholder: "大家怎么称呼你",
      autocomplete: "nickname", enterkeyhint: "go",
    });
    const error = h("p", { class: "muted", role: "alert" }, message);
    const form = h("form", { class: "screen-card" },
      h("h2", {}, "进房间前，起个昵称"),
      input,
      error,
      h("button", { class: "btn primary" }, "进入房间"),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const name = input.value.trim().replace(/\s+/g, " ");
      if (!name) {
        error.textContent = "昵称不能为空";
        return;
      }
      screenEl.hidden = true;
      screenEl.replaceChildren();
      resolve(name);
    });
    screenEl.replaceChildren(form);
    screenEl.hidden = false;
    input.focus();
  });
}
