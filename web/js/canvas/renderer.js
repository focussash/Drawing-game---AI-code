// Draws strokes onto the canvas in logical coordinates. Keeps every stroke so
// the picture can be redrawn crisply after a resize or rotation.

const BACKGROUND = "#ffffff";

export function createRenderer(canvasEl, drawing) {
  const { width: W, height: H } = drawing;
  const ctx = canvasEl.getContext("2d");
  const strokes = new Map();
  let scale = 1;
  let replayCount = 0;

  function resize() {
    const cssW = canvasEl.clientWidth;
    if (!cssW) return; // hidden (e.g. in the lobby)
    const dpr = window.devicePixelRatio || 1;
    const pxW = Math.round(cssW * dpr);
    const pxH = Math.round((pxW * H) / W);
    if (canvasEl.width !== pxW || canvasEl.height !== pxH) {
      canvasEl.width = pxW;
      canvasEl.height = pxH;
    }
    scale = pxW / W;
    redraw();
  }

  function paintBackground() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = BACKGROUND;
    ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);
  }

  function draw(stroke, from = 0) {
    const p = stroke.pts;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = stroke.size;
    ctx.strokeStyle = stroke.color;
    ctx.fillStyle = stroke.color;
    if (p.length === 2) {
      ctx.beginPath();
      ctx.arc(p[0], p[1], stroke.size / 2, 0, Math.PI * 2);
      ctx.fill();
      return;
    }
    const start = Math.max(0, from - 2);
    ctx.beginPath();
    ctx.moveTo(p[start], p[start + 1]);
    for (let i = start + 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]);
    ctx.stroke();
  }

  function redraw() {
    paintBackground();
    for (const stroke of strokes.values()) draw(stroke);
  }

  return {
    resize,
    beginStroke({ id, color, size, x, y }) {
      const stroke = { color, size, pts: [x, y] };
      strokes.set(id, stroke);
      draw(stroke);
    },
    addPoints(id, pts) {
      const stroke = strokes.get(id);
      if (!stroke || pts.length === 0) return;
      const from = stroke.pts.length;
      stroke.pts.push(...pts);
      draw(stroke, from);
    },
    clear() {
      strokes.clear();
      paintBackground();
    },
    replay(list) {
      strokes.clear();
      replayCount += 1;
      list.forEach((s, i) => strokes.set(`replay-${replayCount}-${i}`, { color: s.color, size: s.size, pts: [...s.pts] }));
      redraw();
    },
  };
}
