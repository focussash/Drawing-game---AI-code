// Drawing tools: colors, brush/eraser sizes, eraser toggle and clear.
// Kept deliberately small: brush, eraser, clear, a handful of colors.

import { h } from "../lib/dom.js";

const ERASER_COLOR = "#ffffff";
const COLOR_NAMES = {
  "#000000": "黑色", "#e53935": "红色", "#fb8c00": "橙色", "#fdd835": "黄色",
  "#43a047": "绿色", "#1e88e5": "蓝色", "#795548": "棕色",
};
const SIZE_NAMES = ["细", "中", "粗", "特粗", "超粗"];

const middle = (list) => list[Math.floor((list.length - 1) / 2)];

export function mountToolbar(el, drawing, onClear) {
  const state = {
    tool: "brush",
    color: drawing.colors[0],
    brushSize: middle(drawing.brush_sizes),
    eraserSize: middle(drawing.eraser_sizes),
  };

  function render() {
    const erasing = state.tool === "eraser";
    const sizes = erasing ? drawing.eraser_sizes : drawing.brush_sizes;
    const current = erasing ? state.eraserSize : state.brushSize;
    const biggest = Math.max(...sizes);
    el.replaceChildren(
      h("span", { class: "swatches" }, drawing.colors.map((c) =>
        h("button", {
          class: "swatch", style: `background:${c}`, "aria-label": COLOR_NAMES[c] ?? c,
          "aria-pressed": String(!erasing && state.color === c),
          onclick: () => update({ tool: "brush", color: c }),
        }))),
      h("span", { class: "tool-group" },
        h("span", { class: "sizes" },
          sizes.map((s, i) =>
            h("button", {
              class: "size", "aria-label": `${SIZE_NAMES[i] ?? s}`, "aria-pressed": String(current === s),
              onclick: () => update(erasing ? { eraserSize: s } : { brushSize: s }),
            }, h("i", { style: `width:${dotPx(s, biggest)}px;height:${dotPx(s, biggest)}px` })))),
        h("button", { class: "tool-btn", "aria-pressed": String(erasing),
                      onclick: () => update({ tool: erasing ? "brush" : "eraser" }) }, "橡皮"),
        h("button", { class: "tool-btn", onclick: () => confirm("清空画布？") && onClear() }, "清空"),
      ),
    );
  }

  function update(patch) {
    Object.assign(state, patch);
    render();
  }

  render();
  return {
    getTool() {
      return state.tool === "eraser"
        ? { tool: "eraser", color: ERASER_COLOR, size: state.eraserSize }
        : { tool: "brush", color: state.color, size: state.brushSize };
    },
  };
}

// Preview dot: 4px for the smallest size up to 18px for the biggest.
function dotPx(size, biggest) {
  return Math.max(4, Math.round((size / biggest) * 18));
}
