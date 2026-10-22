// Short-lived message at the bottom of the screen (server errors, copy confirmations).

const SHOW_MS = 3000;
let timer = null;

export function showToast(text) {
  const el = document.getElementById("toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(timer);
  timer = setTimeout(() => {
    el.hidden = true;
  }, SHOW_MS);
}
