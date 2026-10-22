// Pure questions the classic UI asks about the state: who may draw, what each
// 田字格 cell shows, which placeholder the chat box gets, and so on.

const isSpace = (ch) => /\s/.test(ch);

export function canDraw(state) {
  const g = state.game;
  return state.state === "game" && g?.phase === "drawing" && g.drawer === state.you;
}

export function isDrawer(state) {
  return state.game?.drawer === state.you;
}

export function isKnower(state) {
  const g = state.game;
  return Boolean(g) && (g.drawer === state.you || g.correct.includes(state.you));
}

// Each cell: { kind: "blank" | "shown" | "revealed" | "gap", char, index, tappable }.
// null means "nothing to show" (choosing, or guessers without the length hint).
export function hintCells(state) {
  const g = state.game;
  if (!g) return null;
  if (g.phase === "turn_end") {
    const word = g.word ?? g.turn_result?.word;
    return word ? wordCells(word, null, false) : null;
  }
  if (g.phase !== "drawing") return null;
  if (isKnower(state) && g.word) {
    const drawer = isDrawer(state);
    return wordCells(g.word, drawer ? g.template : null, drawer);
  }
  if (!g.template) return null;
  return g.template.map((ch, index) => {
    if (ch === " ") return { kind: "gap", char: "", index, tappable: false };
    if (ch === "_") return { kind: "blank", char: "", index, tappable: false };
    return { kind: "revealed", char: ch, index, tappable: false };
  });
}

function wordCells(word, template, canReveal) {
  const chars = [...word];
  const revealed = (i) => Boolean(template) && template[i] !== "_" && template[i] !== " ";
  const letters = chars.filter((ch) => !isSpace(ch)).length;
  const revealedCount = chars.filter((_, i) => revealed(i)).length;
  const moreAllowed = canReveal && revealedCount < letters - 1;
  return chars.map((ch, index) => {
    if (isSpace(ch)) return { kind: "gap", char: "", index, tappable: false };
    if (revealed(index)) return { kind: "revealed", char: ch, index, tappable: false };
    return { kind: "shown", char: ch, index, tappable: moreAllowed };
  });
}

export function chatPlaceholder(state) {
  const g = state.game;
  if (state.state !== "game" || g?.phase !== "drawing") return "说点什么";
  if (isDrawer(state)) return "只有猜对的人能看到";
  if (g.correct.includes(state.you)) return "只有画手和猜对的人能看到";
  return "输入你的猜测";
}

export function scoreRows(state) {
  const g = state.game;
  return state.players.map((p) => ({
    id: p.id,
    nickname: p.nickname,
    score: g?.scores[p.id] ?? 0,
    drawer: g?.drawer === p.id,
    correct: Boolean(g?.correct.includes(p.id)),
    online: p.online,
    you: p.id === state.you,
  }));
}

export function deltaRows(state) {
  const deltas = state.game?.turn_result?.deltas ?? {};
  const names = Object.fromEntries(state.players.map((p) => [p.id, p.nickname]));
  return Object.entries(deltas)
    .map(([id, points]) => ({ nickname: names[id] ?? "（已离开）", points }))
    .sort((a, b) => b.points - a.points);
}

export function nicknameOf(state, pid) {
  return state.players.find((p) => p.id === pid)?.nickname ?? "";
}
