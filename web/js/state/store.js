// Holds the room state and notifies subscribers with (state, previousState) on every change.

import { applyMessage, initialState } from "./reducers.js";

export function createStore(modeReducers, now = () => Date.now()) {
  let state = initialState();
  const subscribers = new Set();
  return {
    getState: () => state,
    dispatch(msg) {
      const next = applyMessage(state, msg, now(), modeReducers);
      if (next === state) return;
      const prev = state;
      state = next;
      for (const fn of subscribers) fn(state, prev);
    },
    subscribe(fn) {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
  };
}
