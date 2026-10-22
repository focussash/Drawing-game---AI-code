// The shared drawing board: wires renderer, pointer input, toolbar and the
// stroke messages from the server. Which player may draw is decided by the
// current mode (canDraw), not here.

import { StrokeBatcher } from "./batcher.js";
import { attachInput } from "./input.js";
import { createRenderer } from "./renderer.js";
import { mountToolbar } from "../ui/toolbar.js";

// Random start so a drawer who reloads mid-turn never reuses a stroke id.
const randomFirstId = () => 1 + Math.floor(Math.random() * 1_000_000_000);

export function mountBoard({ canvasEl, toolsEl, store, socket, onMessage, canDraw }) {
  let renderer = null;
  let input = null;
  const batcher = new StrokeBatcher((type, data) => socket.send(type, data), randomFirstId());

  function ensure(drawing) {
    if (renderer) return;
    renderer = createRenderer(canvasEl, drawing);
    const toolbar = mountToolbar(toolsEl, drawing, () => {
      if (socket.send("canvas_clear")) renderer.clear();
    });
    input = attachInput(canvasEl, {
      enabled: () => canDraw(store.getState()),
      getTool: () => toolbar.getTool(),
      batcher, renderer, drawing,
    });
    new ResizeObserver(() => renderer.resize()).observe(canvasEl);
    renderer.resize();
  }

  onMessage((msg) => {
    if (msg.type === "welcome") {
      ensure(msg.snapshot.drawing);
      renderer.replay(msg.snapshot.canvas);
      return;
    }
    if (!renderer) return;
    if (msg.type === "stroke_begin") renderer.beginStroke(msg);
    else if (msg.type === "stroke_points") renderer.addPoints(msg.id, msg.pts);
    else if (msg.type === "canvas_clear") renderer.clear();
  });

  function sync(state) {
    const allowed = canDraw(state);
    if (toolsEl.hidden === allowed) toolsEl.hidden = !allowed;
    if (!allowed) input?.finish({ send: false });
  }

  store.subscribe(sync);
  return { refresh: () => sync(store.getState()) };
}
