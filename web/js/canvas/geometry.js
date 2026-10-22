// Screen ↔ logical canvas coordinates. Every device draws in the same logical
// space (1600×1200), so a picture looks identical on phones and desktops.

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export function toLogical(clientX, clientY, rect, width, height) {
  const x = Math.round(((clientX - rect.left) / rect.width) * width);
  const y = Math.round(((clientY - rect.top) / rect.height) * height);
  return [clamp(x, 0, width), clamp(y, 0, height)];
}

export function fitBox(availW, availH, aspect = 4 / 3) {
  const w = Math.floor(Math.min(availW, availH * aspect));
  return { w, h: Math.floor(w / aspect) };
}
