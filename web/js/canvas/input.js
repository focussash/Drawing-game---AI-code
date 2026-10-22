// Pointer input on the canvas (finger, pen or mouse). Draws locally right away
// and hands points to the batcher, which sends them on a short timer.

import { toLogical } from "./geometry.js";

const FLUSH_MS = 40;

export function attachInput(canvasEl, { enabled, getTool, batcher, renderer, drawing }) {
  let pointerId = null;
  let flushTimer = null;

  const point = (e) => toLogical(e.clientX, e.clientY, canvasEl.getBoundingClientRect(), drawing.width, drawing.height);

  function finish({ send = true } = {}) {
    if (pointerId === null) return;
    pointerId = null;
    clearInterval(flushTimer);
    if (send) batcher.end();
    else batcher.abort();
  }

  canvasEl.addEventListener("pointerdown", (e) => {
    if (pointerId !== null || !enabled()) return;
    e.preventDefault();
    pointerId = e.pointerId;
    canvasEl.setPointerCapture?.(e.pointerId);
    const [x, y] = point(e);
    const { tool, color, size } = getTool();
    batcher.begin(tool, color, size, x, y);
    renderer.beginStroke({ id: batcher.current, color, size, x, y });
    flushTimer = setInterval(() => batcher.flush(), FLUSH_MS);
  });

  canvasEl.addEventListener("pointermove", (e) => {
    if (e.pointerId !== pointerId) return;
    if (!enabled()) return finish({ send: false }); // the turn ended mid-stroke
    e.preventDefault();
    const events = e.getCoalescedEvents?.() ?? [e];
    const pts = [];
    for (const ev of events.length ? events : [e]) {
      const [x, y] = point(ev);
      batcher.move(x, y);
      pts.push(x, y);
    }
    renderer.addPoints(batcher.current, pts);
  });

  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
    canvasEl.addEventListener(type, (e) => {
      if (e.pointerId === pointerId) finish();
    });
  }

  // iOS Safari: stop pinch-zoom and page bounce while drawing.
  canvasEl.addEventListener("touchmove", (e) => e.preventDefault(), { passive: false });
  canvasEl.addEventListener("gesturestart", (e) => e.preventDefault());

  return { finish };
}
