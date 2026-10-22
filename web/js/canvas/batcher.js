// Groups pointer moves into few network messages: stroke_begin is sent at once,
// following points are buffered and sent on flush() (called on a short timer).

export const MAX_POINTS_PER_MESSAGE = 400; // flat [x, y, ...] length; must match the server

export class StrokeBatcher {
  constructor(send, firstId = 1) {
    this.send = send;
    this.nextId = firstId - 1;
    this.current = null;
    this.last = null;
    this.buffer = [];
  }

  begin(tool, color, size, x, y) {
    this.end();
    this.nextId += 1;
    this.current = this.nextId;
    this.last = [x, y];
    this.send("stroke_begin", { id: this.current, tool, color, size, x, y });
  }

  move(x, y) {
    if (this.current === null) return;
    if (this.last[0] === x && this.last[1] === y) return;
    this.last = [x, y];
    this.buffer.push(x, y);
  }

  flush() {
    while (this.buffer.length > 0) {
      const pts = this.buffer.splice(0, MAX_POINTS_PER_MESSAGE);
      this.send("stroke_points", { id: this.current, pts });
    }
  }

  end() {
    this.flush();
    this.current = null;
  }

  // Drop the stroke in progress without sending more (e.g. the turn just ended).
  abort() {
    this.buffer = [];
    this.current = null;
  }
}
