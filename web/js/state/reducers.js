// Pure state transitions for the room page. Game-specific messages are
// delegated to the current mode's reducer (see modes/index.js).

export const CHAT_LIMIT = 200;

export function initialState() {
  return {
    status: "connecting", // connecting | online | reconnecting | closed
    closedReason: null,
    you: null, token: null, room: null,
    state: "lobby", mode: null, host: null,
    players: [], lobby: null, drawing: null, limits: null,
    chat: [], game: null, lastResults: null,
  };
}

export function applyMessage(state, msg, now, modeReducers) {
  if (msg.type === "_status") {
    return { ...state, status: msg.status, closedReason: msg.reason ?? state.closedReason };
  }
  if (msg.type === "welcome") return fromWelcome(state, msg, now, modeReducers);
  if (state.you === null) return state; // nothing is meaningful before the snapshot

  switch (msg.type) {
    case "players":
      return { ...state, players: msg.players, host: msg.players.find((p) => p.host)?.id ?? state.host };
    case "lobby": {
      const { type, ...lobby } = msg;
      return { ...state, lobby, lastResults: msg.last_results };
    }
    case "chat":
      return { ...state, chat: [...state.chat, msg.entry].slice(-CHAT_LIMIT) };
    case "game_started":
      return { ...state, state: "game", mode: msg.mode, game: reduceGame(modeReducers, msg.mode, null, { type: "start" }, now) };
    case "game_over":
      return { ...state, state: "lobby", game: null, lastResults: msg.results };
    default: {
      if (state.game === null) return state;
      const game = reduceGame(modeReducers, state.mode, state.game, msg, now);
      return game === state.game ? state : { ...state, game };
    }
  }
}

function fromWelcome(state, msg, now, modeReducers) {
  const s = msg.snapshot;
  return {
    ...state,
    status: "online", closedReason: null,
    you: msg.you, token: msg.token, room: s.room,
    state: s.state, mode: s.mode, host: s.host,
    players: s.players, lobby: s.lobby, drawing: s.drawing, limits: s.limits,
    chat: s.chat.slice(-CHAT_LIMIT),
    game: s.game ? reduceGame(modeReducers, s.mode, null, { type: "snapshot", game: s.game }, now) : null,
    lastResults: s.lobby?.last_results ?? null,
  };
}

function reduceGame(modeReducers, mode, game, msg, now) {
  const reducer = modeReducers[mode];
  return reducer ? reducer(game, msg, now) : game;
}
