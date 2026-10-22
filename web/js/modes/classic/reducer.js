// Classic mode client state. Server sends remaining_ms; we keep an absolute
// local deadline so the countdown is immune to network delay drift.

function emptyGame() {
  return {
    phase: null, round: 0, rounds: 0, drawer: null, deadlineAt: null,
    template: null, word: null, choices: null, extends_left: 0,
    scores: {}, correct: [], turn_result: null,
  };
}

const withDeadline = (game, remainingMs, now) => ({ ...game, deadlineAt: now + remainingMs });

export function reduceClassic(game, msg, now) {
  const g = game ?? emptyGame();
  switch (msg.type) {
    case "start":
      return emptyGame();
    case "snapshot":
      return withDeadline({ ...emptyGame(), ...msg.game }, msg.game.remaining_ms, now);
    case "phase": {
      let next = { ...g, phase: msg.phase, round: msg.round, rounds: msg.rounds, drawer: msg.drawer, template: msg.template };
      if (msg.phase === "choosing") {
        next = { ...next, choices: null, word: null, turn_result: null, correct: [] };
      }
      return withDeadline(next, msg.remaining_ms, now);
    }
    case "choices":
      return { ...g, choices: msg.words };
    case "word":
      return { ...g, word: msg.word };
    case "hint":
      return { ...g, template: msg.template };
    case "timer":
      return withDeadline({ ...g, extends_left: msg.extends_left }, msg.remaining_ms, now);
    case "scores":
      return { ...g, scores: msg.scores, correct: msg.correct };
    case "turn_result":
      return { ...g, turn_result: msg, word: msg.word ?? g.word };
    default:
      return game;
  }
}
