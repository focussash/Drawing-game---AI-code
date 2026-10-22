// Chat log and input. Correct guesses show as a red ✓ with stars; messages
// only people who know the answer can see carry a small tag.

import { h } from "../lib/dom.js";

const STICK_TO_BOTTOM_PX = 40;

export function mountChat(logEl, formEl, inputEl, store, socket) {
  let placeholder = null;

  formEl.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    if (socket.send("chat", { text })) inputEl.value = "";
  });

  store.subscribe((state, prev) => {
    if (state.limits && state.limits !== prev.limits) inputEl.maxLength = state.limits.max_chat_length;
    if (state.chat !== prev.chat) renderLog(logEl, state);
  });

  return {
    setPlaceholder(text) {
      if (text === placeholder) return;
      placeholder = text;
      inputEl.placeholder = text ?? "说点什么";
    },
  };
}

function renderLog(logEl, state) {
  const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < STICK_TO_BOTTOM_PX;
  logEl.replaceChildren(...state.chat.map((entry) => renderEntry(entry, state.you)));
  if (atBottom || state.chat.at(-1)?.from === state.you) logEl.scrollTop = logEl.scrollHeight;
}

function renderEntry(entry, you) {
  if (entry.kind === "system") return h("div", { class: "msg system" }, entry.text);
  const classes = ["msg"];
  if (entry.kind === "correct") classes.push("correct");
  if (entry.from === you) classes.push("mine");
  return h("div", { class: classes.join(" ") },
    h("span", { class: "who" }, entry.nickname),
    entry.kind === "correct" ? `猜对了！ ✓ ${entry.text}` : entry.text,
    entry.private ? h("span", { class: "tag" }, "仅知情者可见") : null,
  );
}
