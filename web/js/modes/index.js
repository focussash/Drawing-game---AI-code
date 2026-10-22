// Registry of client-side game modes. Adding a mode = one reducer + one view.

import { reduceClassic } from "./classic/reducer.js";

export const MODE_REDUCERS = {
  classic: reduceClassic,
};

export const MODE_VIEWS = {
  classic: () => import("./classic/view.js"),
};
