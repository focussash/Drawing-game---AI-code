# AGENTS.md

For AI coding agents (Claude Code, Codex, Cursor, …) and developers working on this repo. If you only want to run the game, read [README.md](README.md).

## What this is

A self-hosted 你画我猜 (Pictionary) for friends spread across the US and mainland China, played in phone browsers. One Python process (FastAPI + uvicorn) serves the static pages and one WebSocket per player. The client is zero-build vanilla ES modules. All state lives in memory. Game rules are pure Python that never touches the network or the real clock, and game modes plug in on both server and client.

## Commands

| Task | Command |
|---|---|
| Environment | `conda env create -f environment.yml && conda activate nhwc`, or a venv plus `pip install -r requirements.txt` (Python ≥ 3.12) |
| Run | `python main.py` (`--config PATH`; `--online` = listen on 127.0.0.1 only and open a localhost.run SSH tunnel) |
| Python tests | `python -m pytest -q` |
| JS tests | `node --test "tests/web/*.test.js"` (keep the quotes and the glob: passing the directory does not work on Node 24) |

- Never `pip install` into a system or conda-base Python. Dependencies are listed once, in `requirements.txt`; `environment.yml` pulls it in with `-r`.
- No npm packages and no build step. `package.json` only sets `"type": "module"` for the Node test runner.
- Both suites must stay green. The batch-file tests in `tests/server/test_scripts.py` run on Windows only.
- Do not run `--online` / `start-online.bat` on your own initiative: it exposes the machine to the internet. Leave that to the person you work for.

## Repository map

```
main.py                 entry point: load config, print addresses, run uvicorn (+ tunnel with --online)
config.toml             every tunable, with Chinese comments; validated by server/config.py
words/*.txt             word banks (only 默认.txt is tracked; others are gitignored)
start-*.bat             Windows double-click launchers; scripts/find-python.bat picks the interpreter
deploy/nhwc.service     systemd unit for a Linux VPS
server/                 pure game logic (no asyncio, no FastAPI, no wall clock)
  room.py               Room: join/resume/kick/host, message dispatch, snapshots, outbox
  room_lobby.py  room_context.py  room_strokes.py  registry.py
  players.py  chatlog.py  canvas_log.py  audience.py  msgparse.py  protocol_limits.py
  config.py  wordbank.py  textnorm.py  clock.py
  modes/base.py         Mode ABC, ModeContext protocol, SettingSpec, validate_settings
  modes/__init__.py     MODES registry
  modes/classic/        the classic mode: settings, scoring, timer, hints, judge, rotation, mode
  net/                  the only asyncio/FastAPI code: app, session, runner, connection, lan, tunnel
web/                    index.html (home), room.html (/r/{CODE}), css/, js/
  js/room.js            room page bootstrap; js/state/ store + reducers; js/net/socket.js
  js/canvas/            geometry, batcher, renderer, input, board
  js/ui/                lobby, chat, players, toolbar, status, banner, viewport, nickname, toast
  js/modes/             client mode registry + classic/{reducer,selectors,format,view}.js
tests/server/           pytest; fakes.py (FakeClock), helpers.py (FakeContext, make_game)
tests/web/              node --test, pure modules only
claude-memory/          design doc, original plan, progress log (see "Docs and workflow")
```

## Architecture

**Server flow.** `net/session.py` accepts the WebSocket and waits for `hello`, then calls `Room.join` and binds a `Connection` to the player id. Each later message goes to `Room.handle(pid, msg)`. The room and its `Mode` never send directly: they append `(Audience, msg)` pairs to an outbox. `net/runner.py` runs one asyncio loop per room. It wakes on `poke()` or at `room.next_deadline()`, calls `room.tick()`, and flushes the outbox into each connection's send queue.

**Rules to keep:**
- Nothing outside `server/net/` imports asyncio or FastAPI, or reads the real time. Time comes from the injected `Clock`, and tests use `FakeClock`.
- The core (room, players, chat, canvas, net) knows nothing about words, phases or scores. Modes talk to the room only through `ModeContext` (implemented by `room_context.py`).
- `Audience` routes messages: `everyone()`, `of(*pids)`, `all_except(*pids)`. Spoiler-free chat depends on it, because players who know the answer get a private channel.
- `Room.handle` must never raise on client input. Malformed messages get an `error` reply.
- Reconnect: the identity token is kept in localStorage, and `hello{token}` resumes the same player. A newer connection replaces the old one (close code 4001). Only the currently bound connection's close marks a player offline (`test_stale_close_does_not_mark_offline`).

**Client.**
- `store.js` plus `reducers.js` are pure state; game messages are delegated to the current mode's reducer.
- A mode view is lazy-imported and exports `mount(shell) → { canDraw(state) }`, where `shell = { store, socket, regions: {topbar, actions, scoreboard, overlay, tools, stage, canvas}, chat, onMessage }`.
- The canvas uses a logical 1600×1200 space.
- Points are batched, at most 200 per message.
- Countdowns use a local deadline: receipt time + `remaining_ms`. This avoids clock skew between continents.
- DOM modules have no automated tests. Check them in a real browser.

## Wire protocol (JSON, every message has `type`)

Client → server:

| type | fields | who |
|---|---|---|
| `hello` | `token?`, `nickname?` | first message, required within 10 s |
| `ping` | – | anyone → `pong` |
| `chat` | `text` | anyone (this is also how guesses are made) |
| `settings` | `values: {key: value}` (partial) | host, lobby only |
| `start` | – | host, lobby only |
| `kick` | `player_id` | host |
| `stroke_begin` | `id, tool: "brush"\|"eraser", color, size, x, y` | `mode.can_draw(pid)` |
| `stroke_points` | `id, pts: [x, y, x, y, …]` (≤ 400 numbers) | same |
| `canvas_clear` | – | same |
| `action` | `name, data` | mode-defined; classic: `choose{index}`, `reveal{index}`, `extend{}`, `skip{}` |

Server → client (core):

| type | fields |
|---|---|
| `welcome` | `you, token, snapshot` (room, state, mode, host, players, lobby, drawing, limits, chat, canvas, game) |
| `players` | `players: [{id, nickname, online, host}]` in join order |
| `lobby` | `specs: [SettingSpec], values, banks, last_results` |
| `chat` | `entry: {from, nickname, text, kind: "chat"\|"correct"\|"system", private}` |
| `stroke_begin` / `stroke_points` / `canvas_clear` | relayed to everyone but the drawer |
| `game_started` | `mode` |
| `game_over` | `results: [{id, nickname, score}]` (descending) |
| `error` | `code, message` (Chinese) |
| `kicked`, `pong` | – |

Classic mode: `phase {phase: choosing|drawing|turn_end, round, rounds, drawer, remaining_ms, template, extends_left}`, `choices {words}` (drawer only), `word {word}` (drawer and each correct guesser), `hint {template}`, `timer {remaining_ms, extends_left}`, `scores {scores, correct}`, `turn_result {word, reason, drawer, deltas}`.

Error codes: `room_not_found room_full banned need_nickname bad_nickname not_allowed bad_message bad_settings not_enough_players no_words`.

Close codes: 4000 handshake failed, 4001 replaced by a newer connection, 4003 kicked, 4004 room not found.

## Adding a game mode

1. Create `server/modes/<name>/` with a `Mode` subclass. It needs:
   - `name`;
   - `parse_mode_config(raw)`, which raises `ConfigError`;
   - `setting_specs(cfg, banks)`;
   - the hooks in `base.py` (`start`, `on_chat`, `on_action`, `on_tick`, `next_deadline`, `on_player_*`, `can_draw`, `snapshot_for`).

   It ends the game with `ctx.finish(results)`.
2. Register the mode in `MODES` (`server/modes/__init__.py`).
3. Add a `[modes.<name>]` section to `config.toml` with Chinese comments.
4. Client side: add `web/js/modes/<name>/reducer.js` and `view.js`. The reducer is pure `(game, msg, now) → game` and must handle `start` and `snapshot`; the view exports `mount(shell)`. Register both in `web/js/modes/index.js`.
5. Tests: follow `tests/server/test_classic_*.py` (using `FakeContext` / `make_game`) and `tests/web/classic*.test.js`.

There is no mode picker yet: `Room` is created with `DEFAULT_MODE = "classic"`. The first new mode also needs a lobby setting that chooses the mode. That is a small change to the core.

## Conventions

- One responsibility per file. Split a file before it grows much past 300 lines.
- **All user-facing text is Simplified Chinese**: UI, error messages, config comments, README. Code, identifiers and code comments are English.
- **Nothing hard-coded.** Tunables go in `config.toml`, whose errors must name the offending key, or in a mode's `SettingSpec` list. Protocol limits live in `protocol_limits.py`; canvas constants in `canvas_log.py`, mirrored in `web/js/canvas/batcher.js`.
- **No external URLs in pages** (CDNs, Google Fonts, analytics): many players are in mainland China. Use system fonts only.
- Test first. Every bug fix comes with a regression test.
- `.bat` files must be UTF-8 without BOM, with CRLF line endings (`.gitattributes` enforces CRLF), and start with `chcp 65001`. Don't generate them through shell `printf` or `echo`, which eats backslashes such as `\f` and `\e`.
- On Windows, aim loopback traffic at `127.0.0.1`, not `localhost`. `localhost` resolves to `::1` first, and the server listens on IPv4.
- Word banks are UTF-8 (BOM allowed) or GB18030/GBK, one word per line, with `#` comments. A test requires `默认.txt` to have at least 200 valid words.

## Testing tips

- Tabs on the same origin share localStorage, so they share one identity. To act as two players on one machine, use `http://localhost:8000` in one tab and `http://127.0.0.1:8000` in another.
- `pytest.ini` filters Starlette's TestClient/httpx deprecation warning.

## Docs and workflow

- `claude-memory/DESIGN.md`: the approved product spec, in Chinese. Entries marked 〔我定〕 are decisions the agent made on the owner's behalf.
- `claude-memory/DEVELOPMENT_PLAN.md`: the original 17-task plan, fully executed. It is a historical record; the Python paths in it are from the original author's machine.
- `claude-memory/achievements.md`: the progress log. Add an entry after each step of new work, with test counts, files changed and any deviations.
- Read these before starting non-trivial work. For a new feature (the planned next one is 联想模式): write a design doc and get the maintainer's approval, then write a plan, then implement it with TDD.
- Do not rewrite an approved design or plan without explicit approval.
- Known limitations:
  - there is no rate limiting;
  - iOS Safari's keyboard handling and WeChat's in-app browser have not been verified on real devices;
  - once a drawing passes 100k coordinates, new strokes are no longer relayed.
