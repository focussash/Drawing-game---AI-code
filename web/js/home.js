// Home page: create a room, or jump to one by its code.

import { mountWeChatHint } from "./ui/banner.js";

mountWeChatHint(document.getElementById("hint"));

const CODE_RE = /^[A-Z0-9]{4}$/;
const error = document.getElementById("error");

document.getElementById("create").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  error.textContent = "";
  try {
    const res = await fetch("/api/rooms", { method: "POST" });
    if (!res.ok) throw new Error(String(res.status));
    const { code } = await res.json();
    location.href = `/r/${code}`;
  } catch {
    error.textContent = "创建房间失败，请检查网络后再试一次";
    button.disabled = false;
  }
});

document.getElementById("join").addEventListener("submit", (event) => {
  event.preventDefault();
  const code = document.getElementById("code").value.trim().toUpperCase();
  if (!CODE_RE.test(code)) {
    error.textContent = "房间码是 4 位字母或数字";
    return;
  }
  location.href = `/r/${code}`;
});
