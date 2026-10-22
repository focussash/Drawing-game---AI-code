// WebSocket that keeps itself connected. Phones drop sockets when the browser
// goes to the background, so we reconnect with backoff and re-check the link
// as soon as the page becomes visible again.

const BACKOFF_MS = [500, 1000, 2000, 4000, 5000];
const PING_INTERVAL_MS = 20000;
const PONG_TIMEOUT_MS = 3000;

// Server close codes after which reconnecting would not help.
const FINAL_CLOSES = { 4000: "rejected", 4001: "replaced", 4003: "kicked", 4004: "not_found" };

export function socketUrl(code, loc = globalThis.location) {
  const scheme = loc.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${loc.host}/ws/${code}`;
}

export class GameSocket {
  constructor({ url, getHello, onMessage, onStatus }) {
    this.url = url;
    this.getHello = getHello;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
    this.ws = null;
    this.attempt = 0;
    this.stopped = true;
    this.retryTimer = null;
    this.pingTimer = null;
    this.pongTimer = null;
    this.onVisibility = () => {
      if (document.visibilityState === "visible" && !this.stopped) this.checkAlive();
    };
  }

  connect() {
    this.stopped = false;
    document.addEventListener("visibilitychange", this.onVisibility);
    this.open();
  }

  close() {
    this.stopped = true;
    document.removeEventListener("visibilitychange", this.onVisibility);
    clearTimeout(this.retryTimer);
    this.stopTimers();
    this.ws?.close();
  }

  send(type, data = {}) {
    if (this.ws?.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify({ type, ...data }));
    return true;
  }

  open() {
    clearTimeout(this.retryTimer);
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      if (this.ws !== ws) return;
      this.attempt = 0;
      ws.send(JSON.stringify(this.getHello()));
      this.pingTimer = setInterval(() => this.send("ping"), PING_INTERVAL_MS);
    };
    ws.onmessage = (event) => {
      if (this.ws !== ws) return;
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.type === "pong") {
        clearTimeout(this.pongTimer);
        return;
      }
      this.onMessage(msg);
    };
    ws.onclose = (event) => {
      if (this.ws !== ws) return; // an abandoned socket we already replaced
      this.stopTimers();
      const reason = FINAL_CLOSES[event.code];
      if (this.stopped || reason) {
        this.stopped = true;
        this.onStatus("closed", reason ?? null);
        return;
      }
      this.onStatus("reconnecting");
      this.scheduleRetry();
    };
  }

  // After the page comes back from the background, a socket can look open but be dead.
  checkAlive() {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      this.onStatus("reconnecting");
      this.open();
      return;
    }
    this.send("ping");
    clearTimeout(this.pongTimer);
    this.pongTimer = setTimeout(() => this.replaceDeadSocket(), PONG_TIMEOUT_MS);
  }

  replaceDeadSocket() {
    const dead = this.ws;
    this.ws = null;
    this.stopTimers();
    try {
      dead?.close();
    } catch {
      /* already gone */
    }
    this.onStatus("reconnecting");
    this.open();
  }

  scheduleRetry() {
    const delay = BACKOFF_MS[Math.min(this.attempt, BACKOFF_MS.length - 1)];
    this.attempt += 1;
    this.retryTimer = setTimeout(() => this.open(), delay);
  }

  stopTimers() {
    clearInterval(this.pingTimer);
    clearTimeout(this.pongTimer);
  }
}
