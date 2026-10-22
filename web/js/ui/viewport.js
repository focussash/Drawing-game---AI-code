// Keep the game screen inside the part of the page the user can actually see.
// When the phone keyboard opens, iOS shrinks the *visual* viewport but not the
// page, so the chat box would hide behind the keyboard. We mirror the visual
// viewport into CSS variables that the in-game layout uses.

export function trackVisualViewport(root = document.documentElement) {
  const vv = window.visualViewport;
  if (!vv) return;
  const update = () => {
    root.style.setProperty("--app-height", `${Math.round(vv.height)}px`);
    root.style.setProperty("--app-top", `${Math.round(vv.offsetTop)}px`);
  };
  vv.addEventListener("resize", update);
  vv.addEventListener("scroll", update);
  update();
}
