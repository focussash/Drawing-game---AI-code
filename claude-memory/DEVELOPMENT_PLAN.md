# 你画我猜 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一个手机浏览器就能玩的多人你画我猜：经典模式、可配置规则、自定义词库、断线重连，核心与玩法模式解耦。

**Architecture:** 一个 Python asyncio 进程（FastAPI + uvicorn）同时提供静态网页和 WebSocket。游戏规则是不碰网络、不读真实时钟的纯逻辑（Room + Mode），由每个房间一个的 RoomRunner 驱动：收到消息或到达截止时间就调用纯逻辑，再把产生的消息发出去。前端是零构建的原生 ES modules，纯逻辑部分（状态归约、坐标、笔画打包）用 `node --test` 测试。

**Tech Stack:** Python 3.13.1、FastAPI、uvicorn[standard]、pytest、httpx（TestClient）；原生 HTML/CSS/JS + Canvas；Node 24 内置测试器（仅测试用，不装 npm 包）。

**Spec:** `claude-memory/DESIGN.md`（本计划依据它；执行时两份都要读）

## Global Constraints

- Python 只用 `E:\MiniConda\envs\biomotum\python.exe`（3.13.1），pip 只装进这个环境。下文 `PY` 指这个路径。
- 运行时依赖只有 `fastapi`、`uvicorn[standard]`；测试依赖 `pytest`、`httpx`（已装）。前端零依赖、零构建，页面不引用任何外部 URL（CDN、Google 字体等），字体只用系统字体。
- JS 测试只用 `node --test`，不装任何 npm 包；仓库根目录的 `package.json` 只写 `{"private": true, "type": "module"}`。
- 每个文件单一职责。游戏规则数值一律来自 `config.toml` 或模式设置项，代码里不写死；协议限制和画布坐标空间统一写在"共享约定"里的那几个常量中。
- 界面文字全部中文。
- 每个任务的收尾：跑全部测试（`PY -m pytest tests -q`，有 JS 改动时加 `node --test tests/web/`）→ 更新 `claude-memory/achievements.md`（测试数、新增/修改的文件、和计划不一致的地方）→ `git commit`。commit message 结尾加两行：`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` 和 `Claude-Session: https://claude.ai/code/session_01HgK171iRKvBrtQJBChrEVe`。
- **停顿点（用户 2026-10-21 指示，优先于 CLAUDE.md 的"每个子项目都停"）**：用户放手让 Claude 做，只在用户能实际试玩的节点停下等确认，即子项目 4、5、6 结束时。子项目 1–3 验证通过后，把结果记进 achievements.md 就直接继续。
- **删除任何文件或文件夹之前，必须先告诉用户并得到同意**；和当前任务无关的文件不要动。
- 每个任务开始前：重读本文件和 `achievements.md`。
- 修改本文件前必须先征得用户同意。

## Review Focus

1. **重连竞态**：手机重连后，旧连接的断开事件姗姗来迟，可能把刚连回来的玩家又标成掉线。预期：只有"当前绑定的连接"断开才算掉线。→ Task 8 `test_stale_close_does_not_mark_offline`
2. **朋友发来的词库文件**：用 Windows 记事本保存的 txt 可能是 GBK 编码、带 BOM、CRLF 换行。预期：都能正确读出来。→ Task 2 `test_load_bank_handles_bom_crlf_comments`、`test_load_bank_falls_back_to_gbk`
3. **畸形或恶意的客户端消息**：类型不对、字段缺失、超长、坐标越界、非画手发笔画。预期：回一个 `error`，房间照常运行，永不抛异常。→ Task 7 `test_malformed_messages_never_raise`
4. **手机在换人的瞬间短暂切到后台**：预期：短暂掉线的人仍算在场，不会因此结束整局；画手掉线超过宽限时间就跳过这一轮，不会卡死。→ Task 6 `test_briefly_offline_player_still_counts_for_min_players`、`test_drawer_offline_skips_after_grace`
5. **知道答案的人再次说出答案**：已猜对的人或画手说出答案时不能泄露给其他人，也不能重复加分；带空格、标点、全角的猜测要能判对。→ Task 5 `test_is_correct_*`、Task 6 `test_knower_message_with_answer_stays_private`

---

## 共享约定

### 常量（`server/canvas_log.py` 和 `server/protocol_limits.py`）

| 常量 | 值 |
|---|---|
| `CANVAS_WIDTH`, `CANVAS_HEIGHT` | 1600, 1200（逻辑坐标，4:3） |
| `MAX_POINTS_PER_MESSAGE` | 400（扁平数组长度，即 200 个点） |
| `MAX_POINTS_PER_DRAWING` | 100_000（扁平数组总长，超出的笔画忽略） |
| `ERASER_COLOR` | `"#ffffff"`（画布底色白，橡皮 = 白色笔） |
| `HELLO_TIMEOUT_SECONDS` | 10 |
| WebSocket 关闭码 | 4001 被新连接顶替、4003 被踢、4004 房间不存在、4000 握手失败 |

### `config.toml`（完整默认文件；dataclass 默认值必须与之一致，空文件也能跑）

```toml
[server]
host = "0.0.0.0"
port = 8000

[room]
max_players = 12
min_players = 2
away_after_seconds = 60          # 掉线超过这么久算"离开"：转移房主、不计入最少人数、等待界面里移除
drawer_offline_skip_seconds = 15
empty_room_ttl_seconds = 600
chat_history = 100
max_chat_length = 60
max_nickname_length = 12

[words]
dir = "words"                    # 相对于本文件所在目录

[drawing]
colors = ["#000000", "#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#795548"]
brush_sizes = [4, 8, 16, 32]
eraser_sizes = [16, 32, 64]

[modes.classic]
default_banks = ["默认"]
rounds = 3
draw_seconds = 80
choose_seconds = 15
word_choices = 3
show_length_hint = true
shorten_after_first_correct = true
shorten_to_seconds = 20
extend_seconds = 10
max_extends_per_turn = 3
reveal_seconds = 6

[modes.classic.scoring]
guesser_max = 100
guesser_min = 20
drawer_per_guess = 25
reveal_factor = 0.75
```

（与企划的差异：企划里的 `host_transfer_seconds` 合并为 `away_after_seconds`，同一个"离开"概念用于转移房主、最少人数判断和等待界面清理。）

### 协议（JSON，每条都有 `type`）

**客户端 → 服务器**

| type | 字段 | 谁能发 |
|---|---|---|
| `hello` | `token?: str`, `nickname?: str` | 连接后第一条，必须 |
| `ping` | – | 任何人 → 回 `pong` |
| `chat` | `text: str`（≤ max_chat_length，非空白） | 任何人 |
| `settings` | `values: {key: value}`（部分更新） | 房主，仅等待界面 |
| `start` | – | 房主，仅等待界面 |
| `kick` | `player_id: str` | 房主，不能踢自己 |
| `stroke_begin` | `id: int, tool: "brush"\|"eraser", color: str, size: int, x: int, y: int` | `mode.can_draw(pid)` |
| `stroke_points` | `id: int, pts: int[]`（扁平 `[x,y,x,y…]`，偶数长度） | 同上 |
| `canvas_clear` | – | 同上 |
| `action` | `name: str, data: object` | 由模式判断。经典模式：`choose{index}`、`reveal{index}`、`extend{}`、`skip{}` |

**服务器 → 客户端（核心）**

| type | 字段 |
|---|---|
| `welcome` | `you: str, token: str, snapshot: Snapshot` |
| `players` | `players: [{id, nickname, online, host}]`（进房顺序） |
| `lobby` | `specs: [SettingSpec]`, `values: {}`, `banks: [str]`, `last_results: [{id, nickname, score}] \| null` |
| `chat` | `entry: {from: str\|null, nickname: str, text: str, kind: "chat"\|"correct"\|"system", private: bool}` |
| `stroke_begin` / `stroke_points` / `canvas_clear` | 与上行相同字段，转发给除画手外的所有人 |
| `game_started` | `mode: str` |
| `game_over` | `results: [{id, nickname, score}]`（分数降序） |
| `error` | `code: str, message: str`（中文） |
| `kicked` | – |
| `pong` | – |

错误码：`room_not_found` `room_full` `banned` `need_nickname` `bad_nickname` `not_allowed` `bad_message` `bad_settings` `not_enough_players` `no_words`

**服务器 → 客户端（经典模式）**

| type | 字段 | 发给 |
|---|---|---|
| `phase` | `phase: "choosing"\|"drawing"\|"turn_end", round, rounds, drawer, remaining_ms, template: str[]\|null` | 所有人 |
| `choices` | `words: [str]` | 只发画手 |
| `word` | `word: str` | 画手；每个刚猜对的人 |
| `hint` | `template: str[]` | 所有人 |
| `timer` | `remaining_ms: int, extends_left: int` | 所有人 |
| `scores` | `scores: {pid: int}, correct: [pid]` | 所有人 |
| `turn_result` | `word: str\|null, reason: "time"\|"all_correct"\|"skipped"\|"drawer_left", drawer, deltas: {pid: int}` | 所有人 |

`SettingSpec` 的 JSON 形式：`{key, label, kind: "int"|"bool"|"banks", default, min, max}`。

**Snapshot**（`welcome.snapshot`）：

```
{ room, state: "lobby"|"game", mode: "classic", host, players: [...同 players 消息],
  lobby: {...同 lobby 消息},
  drawing: {width: 1600, height: 1200, colors, brush_sizes, eraser_sizes},
  limits: {max_chat_length, max_nickname_length},
  chat: [entry...]（该玩家可见的历史）, canvas: [{tool, color, size, pts}],
  game: ClassicSnapshot | null }
ClassicSnapshot = {phase, round, rounds, drawer, remaining_ms, template, word?(知情者), choices?(选词阶段的画手),
                   extends_left, scores, correct}
```

### 文件结构

```
config.toml  requirements.txt  package.json  main.py  README.md  .gitignore
words/默认.txt
server/
  config.py          配置 dataclass + 加载/校验
  textnorm.py        规范化、字数、星号
  wordbank.py        词库扫描/读取、WordPool
  clock.py           Clock 协议、SystemClock
  audience.py        消息收件人
  players.py         玩家与昵称
  chatlog.py         按可见性存聊天历史
  canvas_log.py      笔画存储 + 画布常量
  protocol_limits.py 协议常量
  msgparse.py        消息字段校验
  room_lobby.py      等待界面设置与上局结果
  room_context.py    Room 提供给模式的 ModeContext 适配器
  room.py            房间：加入/重连/踢人/房主/分发/快照
  registry.py        房间创建与查找
  modes/
    __init__.py      MODES 注册表、parse_mode_configs
    base.py          Mode 基类、ModeContext、SettingSpec、validate_settings
    classic/
      settings.py  scoring.py  turn_timer.py  hints.py  judge.py  rotation.py  mode.py
  net/
    connection.py    带发送队列的 WebSocket 包装
    runner.py        每房间一个的驱动循环
    session.py       单个 WebSocket 的握手与收发循环
    app.py           create_app
    lan.py           局域网 IP
web/
  index.html  room.html
  css/base.css  css/room.css
  js/home.js  js/room.js
  js/lib/storage.js  js/lib/dom.js
  js/net/socket.js
  js/state/reducers.js  js/state/store.js
  js/canvas/geometry.js  js/canvas/batcher.js  js/canvas/renderer.js  js/canvas/input.js
  js/ui/nickname.js  js/ui/players.js  js/ui/chat.js  js/ui/lobby.js  js/ui/toolbar.js  js/ui/banner.js
  js/modes/index.js
  js/modes/classic/reducer.js  js/modes/classic/format.js  js/modes/classic/view.js
tests/
  server/fakes.py  server/helpers.py  server/test_*.py
  web/*.test.js
```

---

## 子项目 1：骨架与核心容器（纯 Python，无网络）

### Task 1：项目骨架 + 配置加载

**Files:**
- Create: `.gitignore`, `requirements.txt`, `package.json`, `config.toml`, `server/__init__.py`, `server/config.py`, `tests/__init__.py`, `tests/server/__init__.py`, `tests/server/test_config.py`, `claude-memory/achievements.md`
- Modify: `CLAUDE.md`（补 Project Overview、Current dependencies、Architecture 三节）

**Interfaces:**
- Produces: `ConfigError(Exception)`；frozen dataclasses `ServerConfig(host, port)`、`RoomConfig(max_players, min_players, away_after_seconds, drawer_offline_skip_seconds, empty_room_ttl_seconds, chat_history, max_chat_length, max_nickname_length)`、`DrawingConfig(colors: tuple[str,...], brush_sizes: tuple[int,...], eraser_sizes: tuple[int,...])`、`AppConfig(server, room, drawing, words_dir: Path, modes: dict[str, dict])`；`parse_config(text: str, base_dir: Path) -> AppConfig`；`load_config(path: Path) -> AppConfig`

- [ ] **Step 1：初始化仓库和依赖**

`git init`；`.gitignore` 写 `__pycache__/`、`.pytest_cache/`、`*.pyc`；`requirements.txt` 写 `fastapi>=0.115`、`uvicorn[standard]>=0.30`、`pytest>=8`、`httpx>=0.27`；运行 `PY -m pip install -r requirements.txt`。`config.toml` 照抄"共享约定"。`package.json` 照抄 Global Constraints。

- [ ] **Step 2：写失败的测试** `tests/server/test_config.py`

```python
ROOT = Path(__file__).resolve().parents[2]

def test_default_file_loads():
    cfg = load_config(ROOT / "config.toml")
    assert cfg.server.port == 8000 and cfg.room.max_players == 12
    assert len(cfg.drawing.colors) == 7 and cfg.drawing.brush_sizes == (4, 8, 16, 32)
    assert cfg.words_dir == ROOT / "words"
    assert cfg.modes["classic"]["draw_seconds"] == 80

def test_empty_file_equals_defaults(tmp_path):
    cfg = parse_config("", tmp_path)
    assert cfg.room.min_players == 2 and cfg.room.away_after_seconds == 60
    assert cfg.words_dir == tmp_path / "words" and cfg.modes == {}

def test_words_dir_relative_to_config_dir(tmp_path):
    assert parse_config('[words]\ndir = "w"', tmp_path).words_dir == tmp_path / "w"

@pytest.mark.parametrize("text, key", [
    ("[room]\nmax_player = 3", "room.max_player"),            # 未知键（防拼写错误）
    ("[room]\nmax_players = 3\nmin_players = 4", "min_players"),
    ("[room]\nmin_players = 1", "min_players"),                 # 至少 2
    ("[room]\naway_after_seconds = 0", "away_after_seconds"),   # 正整数
    ("[room]\nmax_players = \"12\"", "max_players"),           # 类型
    ('[drawing]\ncolors = ["red"]', "colors"),                  # 必须 #rrggbb
    ("[drawing]\nbrush_sizes = []", "brush_sizes"),
    ("[nosuch]\na = 1", "nosuch"),
])
def test_invalid_config_names_the_key(tmp_path, text, key):
    with pytest.raises(ConfigError, match=re.escape(key)):
        parse_config(text, tmp_path)
```

- [ ] **Step 3：运行，确认失败** — `PY -m pytest tests/server/test_config.py -v` → ImportError
- [ ] **Step 4：实现 `server/config.py`** — 用 `tomllib.loads`；逐节对照 dataclass 字段校验（未知键、类型、`bool` 不能当 `int`、正整数、`min_players` 在 2..max_players、颜色匹配 `^#[0-9a-fA-F]{6}$`）；`[modes]` 下的每个子表原样放进 `modes`（由模式自己校验，见 Task 4）。
- [ ] **Step 5：运行，确认通过** — 同上命令 → 全部 PASS
- [ ] **Step 6：补 CLAUDE.md、建 achievements.md、提交** — `git add -A && git commit -m "feat: project skeleton and config loading"`

### Task 2：文本规范化 + 词库

**Files:**
- Create: `server/textnorm.py`, `server/wordbank.py`, `tests/server/test_textnorm.py`, `tests/server/test_wordbank.py`

**Interfaces:**
- Produces: `normalize(text: str) -> str`、`word_length(word: str) -> int`、`mask(word: str) -> str`；`UnknownBank(Exception)`、`list_banks(words_dir: Path) -> list[str]`、`load_bank(words_dir: Path, name: str) -> list[str]`、`load_banks(words_dir: Path, names: list[str]) -> list[str]`、`WordPool(words: list[str], rng: random.Random)`，带 `.draw(n: int) -> list[str]`、`.mark_used(word: str) -> None`、`.size: int`

- [ ] **Step 1：写失败的测试**

```python
# test_textnorm.py
def test_normalize_strips_space_punct_and_folds_width_case():
    assert normalize(" 长 颈\u3000鹿！") == "长颈鹿"
    assert normalize("ＡＢＣ") == "abc"
    assert normalize("Hello, World") == "helloworld"
    assert normalize("!!! ") == ""

def test_word_length_ignores_spaces():
    assert word_length("长颈鹿") == 3 and word_length("hello kitty") == 10
    assert mask("hello kitty") == "*" * 10

# test_wordbank.py
def test_list_banks_sorted_txt_stems(tmp_path):  # a.txt b.txt notes.md → ["a", "b"]
def test_load_bank_handles_bom_crlf_comments(tmp_path):
    (tmp_path / "a.txt").write_bytes("\ufeff# 注释\r\n苹果\r\n\r\n香蕉\n苹果\n！！\n".encode("utf-8"))
    assert load_bank(tmp_path, "a") == ["苹果", "香蕉"]       # 去重保序；规范化后为空的行丢弃
def test_load_bank_falls_back_to_gbk(tmp_path):
    (tmp_path / "g.txt").write_bytes("长颈鹿\n熊猫\n".encode("gbk"))
    assert load_bank(tmp_path, "g") == ["长颈鹿", "熊猫"]
def test_load_bank_rejects_unknown_and_traversal(tmp_path):
    for name in ["missing", "../secret", "a/b"]:
        with pytest.raises(UnknownBank): load_bank(tmp_path, name)
def test_load_banks_union_dedup(tmp_path):  # a: 苹果 香蕉 ; b: 香蕉 熊猫 → ["苹果", "香蕉", "熊猫"]
def test_pool_draws_distinct(): assert len(set(WordPool(list("abc"), Random(0)).draw(2))) == 2
def test_pool_prefers_unused_then_refills():
    pool = WordPool(["a", "b", "c"], Random(0)); pool.mark_used("a"); pool.mark_used("b")
    assert pool.draw(1) == ["c"]
    three = pool.draw(3); assert "c" in three and len(set(three)) == 3
def test_pool_smaller_than_n(): assert WordPool(["a"], Random(0)).draw(3) == ["a"]
```

- [ ] **Step 2：运行，确认失败** — `PY -m pytest tests/server/test_textnorm.py tests/server/test_wordbank.py -v`
- [ ] **Step 3：实现** — `normalize`：先 `unicodedata.normalize("NFKC")`，再 `casefold()`，然后丢掉 Unicode 类别以 `P`、`S`、`Z`、`C` 开头的字符。`load_bank`：`name` 必须在 `list_banks()` 里才读；读取时先试 `utf-8-sig`，失败再用 `gb18030`。`WordPool.draw`：先从未用过的词里随机取，不够再从用过的词里补，同一次返回的词互不重复。
- [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: text normalization and word banks`

### Task 3：核心状态容器（玩家、收件人、聊天、画布、消息校验）

**Files:**
- Create: `server/clock.py`, `server/audience.py`, `server/players.py`, `server/chatlog.py`, `server/canvas_log.py`, `server/protocol_limits.py`, `server/msgparse.py`, `tests/server/fakes.py`, `tests/server/test_players.py`, `tests/server/test_containers.py`, `tests/server/test_msgparse.py`

**Interfaces:**
- Produces:
  - `Clock`（Protocol，`now() -> float`）、`SystemClock`（基于 `time.monotonic`）；`tests/server/fakes.py: FakeClock(start=1000.0)`，带 `.now()`、`.advance(seconds)`
  - `Audience`（frozen）：`Audience.everyone()`、`Audience.of(*pids)`、`Audience.all_except(*pids)`、`.includes(pid) -> bool`
  - `RoomFull`、`InvalidNickname`、`clean_nickname(raw: str, max_len: int) -> str`；`Player(id, token, nickname, seq, online=True, offline_since: float|None=None)`；`PlayerList(max_players, max_nickname_length)`，带 `.add(nickname) -> Player`、`.get(pid)`、`.by_token(token)`、`.remove(pid)`、`.ordered() -> list[Player]`、`.ids() -> list[str]`、`.set_online(pid)`、`.set_offline(pid, now)`、`.is_away(pid, now, away_after) -> bool`、`__len__`
  - `ChatLog(limit)`，带 `.append(audience, entry: dict)`、`.visible_to(pid) -> list[dict]`、`.clear()`
  - `CanvasLog(max_points=MAX_POINTS_PER_DRAWING)`，带 `.begin(stroke_id, tool, color, size, x, y) -> None`、`.extend(stroke_id, pts) -> bool`、`.clear()`、`.snapshot() -> list[dict]`；以及共享约定里的常量
  - `BadMessage(Exception)`、`req_str(d, key, max_len, allow_blank=False) -> str`、`req_int(d, key, lo, hi) -> int`、`req_int_list(d, key, max_len, lo, hi) -> list[int]`、`req_dict(d, key) -> dict`

- [ ] **Step 1：写失败的测试**

```python
# test_players.py
def test_clean_nickname():
    assert clean_nickname("  小  王 ", 12) == "小 王"
    assert clean_nickname("a" * 20, 12) == "a" * 12
    with pytest.raises(InvalidNickname): clean_nickname("   ", 12)
def test_add_dedupes_and_limits():
    pl = PlayerList(max_players=3, max_nickname_length=12)
    a, b, c = pl.add("小王"), pl.add("小王"), pl.add("小王")
    assert (b.nickname, c.nickname) == ("小王2", "小王3")
    assert len({a.id, b.id, c.id}) == 3 and len({a.token, b.token, c.token}) == 3
    with pytest.raises(RoomFull): pl.add("x")
    assert pl.by_token(a.token) is a and pl.ids() == [a.id, b.id, c.id]
def test_away_threshold():
    pl = PlayerList(4, 12); p = pl.add("a"); pl.set_offline(p.id, now=100)
    assert not pl.is_away(p.id, 159, 60) and pl.is_away(p.id, 160, 60)
    pl.set_online(p.id); assert p.online and p.offline_since is None
def test_remove_keeps_order(): # add a b c, remove b → ids == [a, c]

# test_containers.py
def test_audience():
    assert Audience.everyone().includes("p1")
    assert not Audience.of("p1").includes("p2")
    e = Audience.all_except("p1"); assert not e.includes("p1") and e.includes("p2")
def test_chatlog_visibility_and_limit():
    log = ChatLog(limit=2)
    log.append(Audience.everyone(), {"t": 1}); log.append(Audience.of("p1"), {"t": 2}); log.append(Audience.everyone(), {"t": 3})
    assert log.visible_to("p2") == [{"t": 3}] and log.visible_to("p1") == [{"t": 2}, {"t": 3}]
def test_canvas_log_roundtrip():
    c = CanvasLog(); c.begin(1, "brush", "#000000", 8, 10, 20)
    assert c.extend(1, [30, 40, 50, 60]) and not c.extend(99, [1, 2])
    assert c.snapshot() == [{"tool": "brush", "color": "#000000", "size": 8, "pts": [10, 20, 30, 40, 50, 60]}]
    c.clear(); assert c.snapshot() == []
def test_canvas_log_point_budget():
    c = CanvasLog(max_points=6); c.begin(1, "brush", "#000000", 8, 0, 0)
    assert c.extend(1, [1, 1, 2, 2]) and not c.extend(1, [3, 3])

# test_msgparse.py
def test_req_str(): # ok / 超长 / 非字符串 / 空白(默认拒绝) 各一例 → BadMessage
def test_req_int_rejects_bool_and_range(): # True → BadMessage; 7 超出 0..5 → BadMessage; 3 → 3
def test_req_int_list(): # [1,2] ok; 超长、含非整数、越界 → BadMessage
def test_req_dict(): # {} ok; [] → BadMessage; 缺键 → BadMessage
```

- [ ] **Step 2：运行，确认失败**
- [ ] **Step 3：实现** — 重名后缀从 2 开始递增；玩家 id 用 `"p{seq}"`，token 用 `secrets.token_urlsafe(16)`。
- [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: core state containers`

**子项目 1 验证：** `PY -m pytest tests -v` 全绿。测试数和文件清单记进 achievements.md，然后直接继续。

---

## 子项目 2：经典模式与房间（纯逻辑，用 FakeClock）

### Task 4：模式框架与经典模式设置项

**Files:**
- Create: `server/modes/__init__.py`, `server/modes/base.py`, `server/modes/classic/__init__.py`, `server/modes/classic/settings.py`, `tests/server/test_settings.py`

**Interfaces:**
- Consumes: `ConfigError`（Task 1）、`Audience`（Task 3）、`WordPool`（Task 2）
- Produces:
  - `base.py`：
    - `SettingSpec(key, label, kind: Literal["int","bool","banks"], default, min=None, max=None)`（frozen），带 `.to_json() -> dict`
    - `SettingsError(Exception)`，带 `.key`
    - `defaults_from(specs) -> dict`
    - `validate_settings(specs, current: dict, updates: dict, banks: list[str]) -> dict`：返回合并后的完整设置
    - `ModeContext`（Protocol）：`player_ids() -> list[str]`、`is_online(pid)`、`is_away(pid)`、`is_host(pid)`、`nickname(pid)`、`send(audience, msg)`、`post_chat(audience, entry)`、`clear_canvas()`、`room_config() -> RoomConfig`、`finish(results: list[dict])`
    - `Mode`（ABC）：
      - 类属性 `name: ClassVar[str]`
      - 类方法 `parse_mode_config(raw: dict) -> Any`、`setting_specs(mode_cfg, banks: list[str]) -> list[SettingSpec]`
      - `__init__(ctx, settings: dict, mode_cfg, words: WordPool, rng)`
      - 抽象方法 `start(now)`、`on_chat(pid, text, now)`、`on_action(pid, name, data: dict, now)`、`on_tick(now)`、`next_deadline() -> float|None`、`on_player_joined(pid, now)`、`on_player_offline(pid, now)`、`on_player_online(pid, now)`、`on_player_removed(pid, now)`、`can_draw(pid) -> bool`、`snapshot_for(pid, now) -> dict`
  - `classic/settings.py`：`ScoringConfig(guesser_max, guesser_min, drawer_per_guess, reveal_factor)`、`ClassicConfig(defaults: dict, scoring: ScoringConfig, default_banks: tuple[str,...])`、`parse_classic_config(raw: dict) -> ClassicConfig`、`classic_setting_specs(cfg, banks) -> list[SettingSpec]`
  - `modes/__init__.py`：`MODES: dict[str, type[Mode]]`（Task 6 注册 `"classic"`）、`parse_mode_configs(raw: dict[str, dict]) -> dict[str, Any]`（缺省的模式用空表解析；未知模式名抛 `ConfigError`）

经典模式设置项（key / label / kind / min..max）：`banks` 词库 banks；`rounds` 圈数 int 1..10；`draw_seconds` 作画时长（秒）int 30..300；`choose_seconds` 选词时长（秒）int 5..60；`word_choices` 候选词数量 int 1..5；`show_length_hint` 显示字数 bool；`shorten_after_first_correct` 有人猜对后缩短倒计时 bool；`shorten_to_seconds` 缩短到（秒）int 5..60；`extend_seconds` 每次加时（秒）int 5..60；`max_extends_per_turn` 每轮最多加时次数 int 0..10；`reveal_seconds` 公布答案停留（秒）int 3..20。默认值来自 `[modes.classic]`（缺省时用"共享约定"里的值）；`banks` 的默认值 = `default_banks` 中实际存在的那些，一个都不存在时取 `banks[:1]`。

- [ ] **Step 1：写失败的测试**

```python
def specs(): return classic_setting_specs(parse_classic_config({}), banks=["默认", "动物"])

def test_defaults():
    d = defaults_from(specs())
    assert d["rounds"] == 3 and d["draw_seconds"] == 80 and d["banks"] == ["默认"]
def test_banks_default_falls_back_to_first():
    s = classic_setting_specs(parse_classic_config({}), banks=["动物"])
    assert defaults_from(s)["banks"] == ["动物"]
def test_partial_update_keeps_others():
    cur = defaults_from(specs()); new = validate_settings(specs(), cur, {"rounds": 5}, ["默认", "动物"])
    assert new["rounds"] == 5 and new["draw_seconds"] == 80 and cur["rounds"] == 3
@pytest.mark.parametrize("updates, key", [
    ({"rounds": 0}, "rounds"), ({"rounds": "5"}, "rounds"), ({"show_length_hint": 1}, "show_length_hint"),
    ({"banks": []}, "banks"), ({"banks": ["不存在"]}, "banks"), ({"nope": 1}, "nope"),
])
def test_invalid_updates(updates, key):
    with pytest.raises(SettingsError) as e: validate_settings(specs(), defaults_from(specs()), updates, ["默认", "动物"])
    assert e.value.key == key
def test_config_defaults_checked_against_ranges():
    with pytest.raises(ConfigError, match="draw_seconds"): parse_classic_config({"draw_seconds": 10})
    with pytest.raises(ConfigError, match="reveal_factor"): parse_classic_config({"scoring": {"reveal_factor": 1.5}})
    with pytest.raises(ConfigError, match="bogus"): parse_classic_config({"bogus": 1})
def test_unknown_mode_section():
    with pytest.raises(ConfigError, match="nosuch"): parse_mode_configs({"nosuch": {}})
```

（`reveal_factor` 必须满足 0 < f ≤ 1；`guesser_min` ≤ `guesser_max`。）

- [ ] **Step 2：运行，确认失败** · [ ] **Step 3：实现** · [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: mode framework and classic settings`

### Task 5：经典模式的纯逻辑单元

**Files:**
- Create: `server/modes/classic/scoring.py`, `turn_timer.py`, `hints.py`, `judge.py`, `rotation.py`；`tests/server/test_classic_units.py`

**Interfaces:**
- Produces:
  - `guesser_points(remaining: float, draw_seconds: int, reveals: int, cfg: ScoringConfig) -> int`
    = `round(max(g_min, g_max × min(1, remaining / draw_seconds)) × factor ** reveals)`
  - `drawer_points(reveals: int, cfg) -> int` = `round(drawer_per_guess × factor ** reveals)`
  - `TurnTimer`：属性 `deadline`、`extends_used`；方法 `.start(now, seconds)`、`.remaining(now) -> float`（≥ 0）、`.shorten_to(now, seconds)`（`deadline = min(deadline, now + seconds)`）、`.extend(seconds)`、`.expired(now) -> bool`
  - `HintError`；`WordHint(word)`：属性 `.word`、`.reveals`；方法 `.reveal(index)`、`.can_reveal_more() -> bool`、`.template(show_length: bool) -> list[str] | None`
    - index 是 `word` 里的字符下标
    - 空格位置在 template 里是 `" "`，未揭的字是 `"_"`，已揭的字显示原字
    - 不显示字数且一个字都没揭时，template 返回 `None`
    - 最多揭 `word_length - 1` 个字
  - `is_correct(guess: str, answer: str) -> bool`：答案规范化后非空，并且是猜测规范化后的子串
  - `Rotation(rounds)`：属性 `.round`（从 1 开始）；方法 `.start(ids)`、`.add_late(pid)`（本圈已经画过的人忽略）、`.remove(pid)`、`.next_drawer(ids, eligible: Callable[[str], bool]) -> str | None`（队列空了就用 `ids` 开新一圈，圈数用完返回 None）

- [ ] **Step 1：写失败的测试**

```python
CFG = ScoringConfig(guesser_max=100, guesser_min=20, drawer_per_guess=25, reveal_factor=0.75)
def test_guesser_points():
    assert [guesser_points(r, 80, k, CFG) for r, k in [(80,0),(40,0),(8,0),(100,0),(80,1),(80,2)]] == [100,50,20,100,75,56]
def test_drawer_points(): assert [drawer_points(k, CFG) for k in (0, 1, 2)] == [25, 19, 14]

def test_timer_shorten_and_extend():
    t = TurnTimer(); t.start(0, 80); assert t.remaining(30) == 50
    t.shorten_to(30, 20); assert t.remaining(30) == 20
    t.extend(10); assert t.remaining(30) == 30 and t.extends_used == 1
    assert not t.expired(59.9) and t.expired(60)
def test_shorten_never_lengthens():
    t = TurnTimer(); t.start(0, 80); t.shorten_to(70, 20); assert t.remaining(70) == 10

def test_hint_template_and_reveal():
    h = WordHint("长颈鹿")
    assert h.template(True) == ["_", "_", "_"] and h.template(False) is None
    h.reveal(1); assert h.template(False) == ["_", "颈", "_"] and h.reveals == 1
    for bad in (1, 5, -1):
        with pytest.raises(HintError): h.reveal(bad)
    h.reveal(0)
    with pytest.raises(HintError): h.reveal(2)                    # 不能揭到全部
def test_hint_spaces_and_single_char():
    h = WordHint("hello kitty"); assert h.template(True)[5] == " "
    with pytest.raises(HintError): h.reveal(5)
    assert not WordHint("猫").can_reveal_more()

@pytest.mark.parametrize("guess", ["长颈鹿", "是不是 长颈鹿！", "长颈鹿吧"])
def test_is_correct_contains(guess): assert is_correct(guess, "长颈鹿")
def test_is_correct_width_case(): assert is_correct("ＨＥＬＬＯ Kitty", "hello kitty")
@pytest.mark.parametrize("guess, answer", [("长颈", "长颈鹿"), ("", "长颈鹿"), ("!!!", "!!")])
def test_is_correct_rejects(guess, answer): assert not is_correct(guess, answer)

def test_rotation_rounds():
    r = Rotation(2); ids = ["a", "b", "c"]; r.start(ids)
    assert [r.next_drawer(ids, lambda p: True) for _ in range(6)] == ["a","b","c","a","b","c"]
    assert r.next_drawer(ids, lambda p: True) is None and r.round == 2
def test_rotation_skips_ineligible():
    r = Rotation(1); r.start(["a","b","c"]); el = lambda p: p != "b"
    assert [r.next_drawer(["a","b","c"], el), r.next_drawer(["a","b","c"], el)] == ["a", "c"]
def test_rotation_late_join_and_remove():
    r = Rotation(1); ids = ["a", "b"]; r.start(ids); assert r.next_drawer(ids, lambda p: True) == "a"
    r.add_late("d"); r.add_late("a"); r.remove("b")
    assert r.next_drawer(ids + ["d"], lambda p: True) == "d" and r.next_drawer(ids, lambda p: True) is None
```

- [ ] **Step 2：运行，确认失败** · [ ] **Step 3：实现** · [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: classic mode units`

### Task 6：经典模式状态机

**Files:**
- Create: `server/modes/classic/mode.py`, `tests/server/helpers.py`（`FakeContext`、`make_game`）, `tests/server/test_classic_mode.py`
- Modify: `server/modes/__init__.py`（注册 `MODES["classic"] = ClassicMode`）

**Interfaces:**
- Consumes: Task 4 的 `Mode`/`ModeContext`/`ClassicConfig`；Task 5 全部；`Audience`、`WordPool`、`textnorm.mask`
- Produces: `ClassicMode(Mode)`，`name = "classic"`；发出的消息严格按"共享约定"里的经典模式协议；`finish(results)` 的参数是 `[{"id", "score"}]`，按分数降序（同分时按进房顺序）
- 测试辅助（`tests/server/helpers.py`）：
  - `FakeContext(clock, players: list[str], host: str)`
    - 记录：`.sent: list[tuple[Audience, dict]]`、`.chats: list[tuple[Audience, dict]]`、`.finished: list[dict] | None`、`.canvas_clears: int`
    - 可调：`.online: dict[str, bool]`、`.offline_since: dict[str, float]`
    - `is_away` 按 `room_config().away_after_seconds` 判断
  - `make_game(players=("p1","p2","p3"), words=("长颈鹿",), **settings) -> (mode, ctx, clock)`：已经 `start`；`word_choices` 默认取 1
  - `last(ctx, type, pid=None) -> dict | None`：最后一条该类型且 `pid` 能收到的消息

状态机规则（测试未覆盖的细节按企划 6.2–6.6 实现）：

- 阶段依次为 `choosing → drawing → turn_end → 下一轮`
- 每一轮开始前检查"不算离开的人数 < `min_players`"，成立就 `finish`
- 画手用 `rotation.next_drawer(ctx.player_ids(), ctx.is_online)` 选出
- 进入 `choosing` 时清空画布

- [ ] **Step 1：写失败的测试**（每条测试的断言如下）

```python
def test_start_enters_choosing():            # phase=choosing, drawer=p1, round=1；choices 只发给 p1；canvas_clears == 1
def test_choose_starts_drawing():            # p1 action choose{index:0} → phase=drawing, remaining_ms=80000, template=["_","_","_"]；word 只发给 p1
def test_choose_by_non_drawer_rejected():    # p2 choose → error not_allowed 发给 p2；仍是 choosing
def test_choose_timeout_auto_picks():        # advance(15); on_tick → drawing
def test_correct_guess_masked_and_scored():  # drawing 开始后 advance(10)，p2 说 "是长颈鹿吗"
    # → chat entry kind=correct, text="***", 发给所有人；word 发给 p2；scores: p2=88, p1=25；correct=[p2]
def test_wrong_guess_public():               # p2 说 "熊" → kind=chat, text="熊", private=False, 发给所有人
def test_chat_public_outside_drawing():     # choosing 和 turn_end 阶段里，任何人（包括画手）说出答案也按公开聊天发，不判定、不加分
def test_knower_message_with_answer_stays_private():
    # p2 猜对后再说 "长颈鹿好难" → 收件人只有 {p1, p2}，private=True，分数不变
    # p1（画手）说 "长颈鹿" → 同上，且不加分
def test_first_correct_shortens_timer():     # 猜对时剩 70 → timer remaining_ms=20000；关闭开关时仍是 70000
def test_all_correct_ends_turn():            # p2、p3 都猜对 → phase=turn_end；turn_result reason=all_correct，deltas 含 p1/p2/p3
def test_time_up_then_next_turn():           # advance(80) tick → reason=time；advance(6) tick → choosing，drawer=p2
def test_reveal_penalizes_later_guesses():   # p1 reveal{index:1} → hint template=["_","颈","_"] 发给所有人；之后 p2 立刻猜对 → p2=75，p1=19
def test_reveal_rejected_for_guesser_and_last_char():  # p2 reveal → error；只剩 1 个没揭的字时再揭 → error
def test_extend_up_to_limit():               # p1 连续 extend 3 次 → remaining 增加 30、extends_left=0，每次一条 system 聊天；第 4 次 → error，时间不变
def test_host_skip():                        # host=p1 发 skip → reason=skipped；非房主发 skip → error
def test_drawer_offline_skips_after_grace():
    # 画画中 on_player_offline(p1)：advance(14) tick 仍是 drawing；再 advance(1) tick → reason=drawer_left
    # 另一种情况：掉线 10 秒后 on_player_online → advance(20) tick 仍是 drawing
def test_offline_player_skipped_in_rotation():   # 这一轮结束时 p2 掉线 → 下一个画手是 p3
def test_briefly_offline_player_still_counts_for_min_players():
    # 两人局，min_players=2：p2 掉线（还没到"离开"）时换下一轮 → 没 finish，画手跳过 p2 回到 p1
    # advance(60) 后 p2 算离开 → 下一轮开始时 finish
def test_game_finishes_after_rounds():       # rounds=1、两名玩家各画一轮都超时 → finished == [{"id","score"}…]，按分数降序
def test_late_joiner_guesses_now_draws_later():  # p1 作画时 on_player_joined(p4) → p4 能猜对并得分；画手顺序 p2 → p3 → p4
def test_removed_drawer_ends_turn():         # 画画中 on_player_removed(p1) → reason=drawer_left
def test_removed_last_guesser_completes_turn():  # p2 已猜对，p3 被移除（先从 FakeContext 的玩家列表里删掉，再调 on_player_removed）→ reason=all_correct
def test_snapshot_hides_word():
    # 作画阶段：snapshot_for(p2) 有 template、没有 "word"；snapshot_for(p1) 有 word 和 extends_left
    # 选词阶段：只有 p1 的快照里有 choices
def test_can_draw_only_drawer_while_drawing():
def test_words_not_repeated():               # words=("A","B")，word_choices=1，连续两轮出的词不同
```

- [ ] **Step 2：运行，确认失败** — `PY -m pytest tests/server/test_classic_mode.py -v`
- [ ] **Step 3：实现 `ClassicMode`**
  - `next_deadline()` 取以下几项中的最小值：选词截止、`timer.deadline`、画手掉线跳过点（`drawer_offline_since + drawer_offline_skip_seconds`）、`turn_end` 截止
  - 判断"所有人都猜对"时，只统计在线的非画手；没有任何人猜对时不提前结束
  - `remaining_ms` 用 `round(秒 × 1000)`
- [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: classic mode state machine`

### Task 7：房间

**Files:**
- Create: `server/room_lobby.py`, `server/room_context.py`, `server/room.py`, `server/registry.py`, `tests/server/test_room.py`

**Interfaces:**
- Consumes: Tasks 1–6
- Produces:
  - `JoinError(Exception)`，带 `.code`（`banned`/`room_full`/`need_nickname`/`bad_nickname`）
  - `LobbyState(specs_fn, words_dir)`：
    - 方法 `.refresh_banks() -> list[str]`、`.update(updates) -> None`（抛 `SettingsError`）、`.message() -> dict`（即 `lobby` 消息）
    - 属性 `.values`、`.last_results`
  - `RoomModeContext(room)`：实现 `ModeContext`
  - `Room(code, config: AppConfig, mode_configs: dict, clock: Clock, rng: random.Random)`
    - 方法：`.join(token: str|None, nickname: str|None) -> Player`、`.connect(pid)`、`.disconnect(pid)`、`.handle(pid, msg: dict)`、`.tick()`、`.next_deadline() -> float|None`、`.drain_outbox() -> list[tuple[Audience, dict]]`、`.drain_closes() -> list[str]`、`.is_abandoned() -> bool`、`.snapshot_for(pid) -> dict`
    - 属性：`.players`、`.host_id`、`.state`
  - `RoomRegistry(config, clock, rng)`：方法 `.create() -> Room`、`.get(code) -> Room|None`、`.remove(code)`；属性 `.mode_configs`（构造时调用 `parse_mode_configs`）。房间码为 4 位，字符取自 `ABCDEFGHJKMNPQRSTUVWXYZ23456789`，不重复。

房间规则：

- 第一个 `join` 的人是房主。
- `connect` 时依次做这些事：
  1. 把玩家标成在线；
  2. 游戏进行中就通知模式（新玩家调 `on_player_joined`，老玩家调 `on_player_online`）；
  3. 给本人发 `welcome`；
  4. 广播 `players`。
- `tick` 依次做这些事：
  1. 等待界面里删掉已离开的人；
  2. 房主已离开时，把房主交给最早进房的在线玩家；
  3. 驱动模式的 `on_tick`。
- 模式调用 `finish` 后：
  1. 回到 lobby，`last_results` 附上昵称；
  2. 广播 `game_over` 和 `lobby`；
  3. 删掉已离开的人；
  4. 清空画布。
- 收到的笔画要满足这些条件，否则回 `bad_message`：
  - 颜色在调色板里（橡皮固定用 `ERASER_COLOR`）；
  - 粗细在对应的档位列表里；
  - 坐标在 `0..CANVAS_WIDTH/HEIGHT` 范围内；
  - `pts` 是偶数长度，且不超过 `MAX_POINTS_PER_MESSAGE`。

  合格的笔画写进 `CanvasLog`，再用 `Audience.all_except(画手)` 转发给其他人。
- 等待界面的聊天公开给所有人；游戏中的聊天交给 `mode.on_chat`。
- 以下两个时机调用 `LobbyState.refresh_banks()`：等待界面里有人 connect 时，以及游戏结束回到等待界面时。已选的词库如果被删掉了，就从设置里去掉；一个都不剩时，回退到默认值。

- [ ] **Step 1：写失败的测试**（辅助函数 `make_room(tmp_path, clock, **room_overrides)`：创建 `words/默认.txt`，内容为 长颈鹿/熊猫/苹果/香蕉；`out(room, pid, type)` 取出某人收到的某类消息）

```python
def test_join_and_welcome():          # welcome 只发给本人：you、token 都有，snapshot.state=="lobby"，snapshot.host==本人；players 广播
def test_join_needs_valid_nickname(): # join(None, None) → need_nickname；join(None, "  ") → bad_nickname
def test_resume_with_token():         # disconnect 后 join(p.token, None) is p；connect 后 p.online
def test_unknown_token_with_nickname_joins_new():
def test_room_full():                 # max_players=2 → 第 3 个人 join 抛 room_full
def test_settings_host_only():        # p2 改设置 → not_allowed；房主 {"rounds": 5} → 广播的 lobby 里 values.rounds == 5；{"rounds": 0} → bad_settings
def test_start_checks():              # 只有 1 个在线玩家时 start → not_enough_players；所选词库为空 → no_words
def test_start_creates_game():        # state=="game"，广播 game_started{mode:"classic"}，收到 phase 消息
def test_settings_rejected_in_game(): # → not_allowed
def test_kick():                      # p2 收到 kicked；drain_closes()==[p2.id]；p2 已被移除；join(p2.token, "x") → banned；房主踢自己 → error
def test_host_transfers_when_away():  # 房主掉线后 advance(60) 再 tick → host_id 变成 p2，广播的 players 里 host 标记随之更新
def test_lobby_drops_away_players_game_keeps_them():
def test_stroke_relay_only_from_drawer():  # 画手的笔画转发给其他人（画手本人收不到），并出现在快照的 canvas 里；p2 发的笔画 → not_allowed；颜色不在调色板 → bad_message
@pytest.mark.parametrize("msg", [
    {}, {"type": 5}, {"type": "chat"}, {"type": "chat", "text": "x" * 1000}, {"type": "settings", "values": []},
    {"type": "kick"}, {"type": "stroke_points", "id": 1, "pts": [1]}, {"type": "action", "name": "choose", "data": "x"},
    {"type": "nosuch"}, {"type": "stroke_begin", "id": 1, "tool": "brush", "color": "#000000", "size": 8, "x": 99999, "y": 0},
])
def test_malformed_messages_never_raise(msg):   # lobby 和 game 两种状态下都不抛异常，并且发件人收到 error
def test_lobby_chat_public():
def test_game_over_returns_to_lobby():          # rounds=1 两人局，靠推进时间结束 → state=="lobby"；game_over.results 带昵称；lobby.last_results 同样
def test_abandoned_after_ttl():                 # 所有人掉线：advance(599) 还不算废弃，advance(1) 后算
def test_late_join_gets_game_snapshot():        # 游戏中新加入的人：snapshot.game.phase 存在，canvas 是当前的笔画
def test_registry_codes_unique():               # 用固定种子的 rng 创建 50 个房间，码互不重复；get/remove 正常
```

- [ ] **Step 2：运行，确认失败** · [ ] **Step 3：实现** · [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: room and registry`

**子项目 2 验证：** 全部测试通过。测试里模拟出的完整一局（选词 → 作画 → 猜对 → 揭字 → 加时 → 掉线 → 结束）记进 achievements.md，然后直接继续。

---

## 子项目 3：网络层

### Task 8：连接、房间驱动、应用

**Files:**
- Create: `server/net/__init__.py`, `server/net/connection.py`, `server/net/runner.py`, `server/net/session.py`, `server/net/app.py`, `web/index.html`, `web/room.html`（两个页面先放只有标题"你画我猜"的占位，子项目 4 会替换）, `tests/server/test_app.py`

**Interfaces:**
- Consumes: `RoomRegistry`、`Room`
- Produces:
  - `Connection(ws)`
    - `.send(text: str)`：非阻塞，放进 `asyncio.Queue`
    - `async .run_writer()`
    - `async .close(code: int)`
  - `RoomRunner(room, clock, on_done: Callable[[], None])`
    - `.bind(pid, conn) -> Connection | None`：返回被顶替的旧连接
    - `.unbind(pid, conn) -> bool`：只有 `conn` 是当前绑定的连接才解绑并返回 True
    - `.flush()`：把 `drain_outbox` 的消息按收件人发给已绑定的连接，然后给 `drain_closes` 里的人发关闭码 4003
    - `.poke()`
    - `async .run()`：循环等到 `min(next_deadline, 现在 + 1 秒)`，或者被 `poke` 唤醒，然后 `tick` 并 `flush`；房间被废弃时调用 `on_done` 并退出
  - `async run_session(ws, registry, runners)`：流程见下方 Step 3
  - `create_app(config: AppConfig, clock: Clock | None = None, rng: random.Random | None = None, web_dir: Path = 默认 web/) -> FastAPI`，路由如下：
    - `GET /`：返回 `index.html`
    - `GET /r/{code}`：返回 `room.html`
    - `POST /api/rooms`：返回 `{"code"}`，同时启动这个房间的 runner 任务
    - `WS /ws/{code}`
    - `/static`：挂载 `web/`

- [ ] **Step 1：写失败的测试**（用 `with TestClient(create_app(cfg)) as client:`；`hello(ws, **kw)` 发送 hello 并返回 welcome）

```python
def test_pages_and_room_creation():          # GET / 和 /r/ABCD 返回 200；POST /api/rooms 返回 4 位的 code
def test_hello_welcome_and_players():        # welcome.you 存在；紧接着收到 players，里面有 1 个人
def test_unknown_room_closes_4004():         # 收到 error room_not_found，然后连接以 4004 关闭
def test_first_message_must_be_hello():      # 第一条发 chat → error bad_message，然后以 4000 关闭
def test_ping_pong():
def test_resume_replaces_old_connection():   # ws2 用 ws1 的 token 发 hello → 同一个 you；ws1 被 4001 关闭
def test_stale_close_does_not_mark_offline():  # 接着关掉 ws1 → registry.get(code).players.get(pid).online 仍是 True
def test_chat_roundtrip_two_clients():       # A 发的聊天，B 能收到
def test_kick_closes_4003():
def test_one_turn_over_websocket():          # 两个客户端：房主设 word_choices=1 → start → 画手 choose → 对方猜对 → 双方都收到 turn_result reason=all_correct
```

- [ ] **Step 2：运行，确认失败**
- [ ] **Step 3：实现** — `run_session` 的流程：
  1. `accept`；
  2. 房间不存在：发 `error room_not_found` 并以 4004 关闭；
  3. 在 `HELLO_TIMEOUT_SECONDS` 秒内收 `hello`，`join` 失败就发对应的 `error` 并以 4000 关闭；
  4. `bind`；如果顶替了旧连接，把旧连接以 4001 关闭；
  5. `connect`，然后 `flush` 和 `poke`；
  6. 进入接收循环：收到 `ping` 回 `pong`；不是合法 JSON 对象的消息直接忽略；其余交给 `room.handle`，然后 `flush` 和 `poke`；
  7. 连接断开时，只有 `unbind` 返回 True 才调用 `room.disconnect`。

  `run` 循环里的任何异常都要记日志，并且不能让 runner 退出。
- [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: websocket networking layer`

### Task 9：启动入口

**Files:**
- Create: `main.py`, `server/net/lan.py`, `tests/server/test_main.py`

**Interfaces:**
- Produces: `lan_ip() -> str | None`（用 UDP socket 的 connect 技巧拿本机 IP，失败返回 None）；`main(argv: list[str] | None = None) -> None`（参数 `--config`，默认 `./config.toml`）

- [ ] **Step 1：写失败的测试** — `test_bad_config_exits_with_message`：配置文件写坏时，`main(["--config", str(bad)])` 抛 `SystemExit`，并且 stderr 里有出错的键名。`test_lan_ip_returns_str_or_none`。
- [ ] **Step 2：运行，确认失败**
- [ ] **Step 3：实现** — 启动前打印本机地址和局域网地址，例如 `手机在同一 Wi-Fi 下打开 http://192.168.x.x:8000`；用 `uvicorn.run(app, host, port, ws_ping_interval=20, ws_ping_timeout=20)` 启动。
- [ ] **Step 4：运行，确认通过**；再手动跑一遍 `PY main.py`，然后 `curl -X POST localhost:8000/api/rooms`，应返回房间码
- [ ] **Step 5：achievements + commit** `feat: entry point`

**子项目 3 验证：** 全部测试通过；服务器能起来，能建房间。记进 achievements.md，然后直接继续。

---

## 子项目 4：前端基础（首页、等待界面、聊天、重连）

### Task 10：界面草图（给用户确认）

**Files:**
- Create（临时，放在 scratchpad 里，不进仓库）：`mockup.html`

- [ ] **Step 1**：先用 frontend-design skill 定视觉方向，再画一个静态 HTML 草图，包含手机竖屏的三个画面：
  1. 等待界面：玩家列表、设置、开始按钮；
  2. 作画中（画手视角）：顶栏有轮次、倒计时、可点的字；画布；工具栏；+10 秒和跳过按钮；聊天；
  3. 作画中（猜词视角）：提示 `_ 颈 _`；聊天里能看到 `***` 和错误的猜测。

  再附一个电脑宽屏的布局：画布在左，侧栏放玩家和聊天。
- [ ] **Step 2**：用 SendUserFile 发给用户过目（不用等回复，继续往下做；用户有意见再改），然后把布局要点记进 achievements.md。

### Task 11：前端纯逻辑（Node 测试）

**Files:**
- Create: `web/js/lib/storage.js`, `web/js/state/reducers.js`, `web/js/modes/index.js`, `web/js/modes/classic/reducer.js`, `web/js/modes/classic/format.js`, `tests/web/storage.test.js`, `tests/web/reducers.test.js`, `tests/web/classic.test.js`

**Interfaces:**
- Produces:
  - `storage.js`：`safeGet(key, fallback, store = globalThis.localStorage)`、`safeSet(key, value, store)`，两者都用 try/catch 包住；key 的格式是 `nhwc.nickname` 和 `nhwc.token.<CODE>`
  - `reducers.js`：
    - `initialState()` 返回 `{you, token, room, state, mode, host, players, lobby, drawing, limits, chat, game, lastResults, status}`
    - `applyMessage(state, msg, now, modeReducers) -> state`：纯函数，不认识的 type 原样返回 state
      - 自己处理：`welcome` / `players` / `lobby` / `chat`（最多留 200 条）/ `game_started` / `game_over`
      - 其余消息交给 `modeReducers[state.mode](state.game, msg, now)`
  - `modes/index.js`：`MODE_REDUCERS = {classic: reduceClassic}`、`MODE_VIEWS = {classic: () => import("./classic/view.js")}`
  - `classic/reducer.js`：`reduceClassic(game, msg, now) -> game`
    - 处理的消息：phase / choices / word / hint / timer / scores / turn_result
    - 收到 `remaining_ms` 时，把它换算成 `deadlineAt = now + remaining_ms`
    - 新一轮 `choosing` 开始时，清空 choices、word、turn_result、correct
  - `classic/format.js`：
    - `templateText(template: string[] | null) -> string`：`["_","颈","_"]` 变成 `"_ 颈 _"`；遇到空格元素输出双倍间隔；`null` 变成 `"？"`
    - `secondsLeft(deadlineAt, now) -> int`：向上取整，不小于 0

- [ ] **Step 1：写失败的测试**（`node:test` + `node:assert/strict`）
  - storage：store 的方法会抛异常时，返回 fallback
  - reducers：
    - welcome 之后 you、players、chat 都来自快照，`state === "lobby"`
    - chat 消息追加，并截断到 200 条
    - game_over 之后 state 回到 lobby、game 变成 null、lastResults 已设置
    - 不认识的 type 返回同一个对象
  - classic reducer：
    - phase 消息算出 `deadlineAt === now + remaining_ms`
    - 新的 choosing 会清空 word
    - 收到 hint 时更新 template
  - format：上面列出的各个例子；`secondsLeft(1000 + 1500, 1000) === 2`
- [ ] **Step 2：运行，确认失败** — `node --test tests/web/`
- [ ] **Step 3：实现** · [ ] **Step 4：运行，确认通过**
- [ ] **Step 5：achievements + commit** `feat: frontend state logic`

### Task 12：首页、连接、等待界面、聊天

**Files:**
- Modify: `web/index.html`, `web/room.html`（替换 Task 8 的占位页）
- Create: `web/css/base.css`, `web/css/room.css`, `web/js/home.js`, `web/js/room.js`, `web/js/lib/dom.js`, `web/js/net/socket.js`, `web/js/state/store.js`, `web/js/ui/nickname.js`, `web/js/ui/players.js`, `web/js/ui/chat.js`, `web/js/ui/lobby.js`

**Interfaces:**
- Consumes: Task 11 全部；协议
- Produces:
  - `dom.js`：`h(tag, attrs, ...children)`
  - `GameSocket({url, getHello, onMessage, onStatus})`：方法 `.connect()`、`.send(type, data = {})`、`.close()`
    - 断线后按 0.5、1、2、4、5、5… 秒退避重连
    - 遇到关闭码 4001/4003/4004 不再重连，并通过 `onStatus` 报告原因
    - 每 20 秒发一次 `ping`
    - 收到 `visibilitychange` 且页面变为可见时，立刻发 `ping`；3 秒内没收到 `pong` 就主动断开重连
  - `createStore(modeReducers)`：方法 `.dispatch(msg)`、`.getState()`、`.subscribe(fn)`
  - UI 模块统一导出 `mount(el, store, socket)`：把 DOM 挂到 `el` 上，订阅 store 后按需重绘
- 页面行为：
  - **首页**
    - "创建房间"：`POST /api/rooms`，然后跳转到 `/r/CODE`；
    - "加入"：输入框里填房间码，跳转到 `/r/CODE`。
  - **房间页**
    - 本地存过这个房间的 token 就直接连接；没有的话弹昵称框，并预填上次用过的昵称；
    - `welcome` 之后把 token 和昵称存下来；
    - 被 4001/4003/4004 关闭时，分别提示"已在其他页面打开"、"你被房主移出了房间"、"房间不存在"，并给一个回首页的按钮。
  - **等待界面**
    - 设置表单按 `specs` 生成：int 用数字步进器，bool 用开关，banks 用复选列表；
    - 只有房主能改，改一项就发一次 `settings`；
    - 房主能看到开始按钮和每个人旁边的踢人按钮；
    - 有 `last_results` 时显示上一局排名。
  - **聊天**
    - 输入框的 maxlength 来自 `limits`；
    - `correct` 类消息显示为 "昵称 猜对了！***"，并高亮；
    - `private` 的消息加"仅知情者可见"小标签；
    - `system` 消息用灰色；
    - 新消息来时自动滚到底部。
  - **网络状态**：断线时在顶部显示"重连中…"横条。
  - **玩家列表**：掉线的人显示成灰色，房主名字旁边有标记。
  - **WebSocket 地址**：按 `location.protocol` 选 `ws` 或 `wss`，再拼上 `location.host` 和 `/ws/CODE`，不写死。

- [ ] **Step 1**：实现以上内容。
- [ ] **Step 2：手动验证**（用 claude-in-chrome，开两个标签页，或者让用户用手机连局域网地址）：
  - 建房；两人进房，且重名时自动加后缀；
  - 房主改设置，另一端实时同步；
  - 两边互相聊天；
  - 踢人；
  - 刷新页面后回到原位置；
  - 关掉服务器再重启后，客户端显示"重连中"（房间已经没了，所以最后提示"房间不存在"）。
- [ ] **Step 3**：`node --test tests/web/` 和 pytest 都通过；achievements + commit `feat: home, lobby, chat and reconnect UI`

**子项目 4 验证：** 把 Step 2 的手动验证结果和截图给用户看，并请用户用自己的手机进一次房间试试。**停下等确认**。

---

## 子项目 5：画布与经典模式界面

### Task 13：画布纯逻辑（Node 测试）

**Files:**
- Create: `web/js/canvas/geometry.js`, `web/js/canvas/batcher.js`, `tests/web/canvas.test.js`

**Interfaces:**
- Produces:
  - `toLogical(clientX, clientY, rect, width, height) -> [x, y]`：取整，并夹在 `0..width` 和 `0..height` 之间
  - `fitBox(availW, availH, aspect = 4/3) -> {w, h}`：在可用区域里放得下的最大 4:3 矩形
  - `StrokeBatcher(send)`：
    - `.begin(tool, color, size, x, y)`：id 从 1 开始自增，立即发送 `stroke_begin`
    - `.move(x, y)`：缓存这个点；和上一个点相同就丢掉
    - `.flush()`：缓存非空时才发 `stroke_points`，每条消息最多 200 个点，超出的拆成多条
    - `.end()`：先 `flush`
- [ ] **Step 1：写失败的测试**
  - 矩形四个角映射到 `(0,0)` 和 `(1600,1200)`；矩形外的点被夹住；
  - `fitBox(400, 800)` 得到 `{w: 400, h: 300}`，`fitBox(1000, 300)` 得到 `{w: 400, h: 300}`；
  - batcher 的 begin 会发一条消息；重复的点被丢掉；缓存为空时 flush 不发消息；250 个点拆成 2 条消息；第二次 begin 的 id 是 2。
- [ ] **Step 2：确认失败** · [ ] **Step 3：实现** · [ ] **Step 4：确认通过**
- [ ] **Step 5：achievements + commit** `feat: canvas geometry and stroke batching`

### Task 14：画布渲染、输入、工具栏

**Files:**
- Create: `web/js/canvas/renderer.js`, `web/js/canvas/input.js`, `web/js/ui/toolbar.js`
- Modify: `web/js/room.js`, `web/css/room.css`

**Interfaces:**
- Produces:
  - `createRenderer(canvasEl, drawing)`：
    - 方法：`.beginStroke({id, tool, color, size, x, y})`、`.addPoints(id, pts)`、`.clear()`、`.replay(strokes)`、`.resize()`
    - 支持高分屏（DPR）；本地保留全部笔画，`resize` 时重画
    - 线条用圆头、圆角；橡皮按白色画
  - `attachInput(canvasEl, {enabled(), getTool(), batcher, renderer})`：
    - 用 Pointer Events；画布设 `touch-action: none`
    - 每 40ms 调一次 `batcher.flush`
    - 本地立即画出来，不等服务器回传
  - `toolbar.mount`：画笔/橡皮切换、粗细档位、颜色、清空（先 `confirm("清空画布？")`）。只有 `can_draw` 时才显示，即本人是画手并且处于作画阶段。
- 收到的 `stroke_*` 和 `canvas_clear` 直接交给 renderer，不经过 store；`welcome` 里的 `snapshot.canvas` 用 `replay` 画出来。
- [ ] **Step 1**：实现。
- [ ] **Step 2：手动验证**（两个浏览器，临时把 `word_choices` 设为 1）：
  - 画手画的东西实时出现在对方屏幕上；
  - 橡皮能用，粗细和颜色能换；
  - 清空后两端都空白；
  - 刷新页面后画面完整恢复；
  - 窄窗口和宽窗口里看到的画面比例一致；
  - 在手机上画画时页面不滚动。
- [ ] **Step 3**：achievements + commit `feat: canvas rendering and drawing tools`

### Task 15：经典模式界面

**Files:**
- Create: `web/js/modes/classic/view.js`
- Modify: `web/js/room.js`, `web/css/room.css`

**Interfaces:**
- Produces: `view.js` 导出 `mount(el, store, socket)`，挂载经典模式的全部界面部件；`room.js` 通过 `MODE_VIEWS[state.mode]` 加载，核心不认识任何经典模式的元素
- 界面内容：
  - **顶栏**：`第 x/y 圈`、倒计时（每 250ms 用 `secondsLeft` 刷新一次）、提示区：
    - 猜词的人看到 `templateText`；
    - 知道答案的人看到答案原文；
    - 画手看到的每个字都可以点：点后弹 `confirm("揭示「颈」？之后猜对的人和你得分都会打折")`，确认就发 `action reveal{index}`；已揭的字和空格不能点。
  - **选词阶段**：
    - 画手：看到候选词按钮，点一个发 `action choose{index}`；
    - 其他人：看到"<昵称> 正在选词…"。
  - **作画阶段**：
    - 画手：看到"+N秒（剩 k 次）"按钮，发 `action extend`，次数用完就禁用；
    - 画手的聊天框提示"只有猜对的人能看到"；
    - 已猜对的人在玩家列表里打勾。
  - **房主**：选词和作画阶段都能看到"跳过"按钮，发 `action skip`。
  - **公布阶段**：浮层显示答案、结束原因（时间到 / 全部猜对 / 已跳过 / 画手离开）、本轮每人加分。
  - **分数**：游戏中玩家列表按分数显示。
  - **结束**：收到 `game_over` 后回到等待界面，那里会显示上一局排名（Task 12 已实现）。
- [ ] **Step 1**：实现。
- [ ] **Step 2：手动验证**（3 个浏览器标签页，或用户的几台手机，完整打一局 rounds=1）：
  - 选词超时会自动选词；
  - 猜错的话公开显示，猜对的显示 `***`；
  - 第一个人猜对后倒计时缩短；
  - 揭字后提示同步，得分打折；
  - 加时 3 次后按钮禁用；
  - 房主跳过；
  - 画手切到后台超过 15 秒，这一轮被跳过；
  - 最后显示排名并回到等待界面。
- [ ] **Step 3**：achievements + commit `feat: classic mode UI`

**子项目 5 验证：** 用户和朋友用手机实际打一局，收集反馈。**停下等确认**。

---

## 子项目 6：手机打磨与部署

### Task 16：手机体验与微信提示

**Files:**
- Create: `web/js/ui/banner.js`
- Modify: `web/room.html`, `web/css/base.css`, `web/css/room.css`, `web/js/room.js`

- [ ] **Step 1**：实现以下几点：
  - viewport 加 `width=device-width, initial-scale=1, viewport-fit=cover`；页面高度用 `100dvh`；
  - iOS 弹出键盘时，用 `visualViewport` 的 resize 事件让输入框保持可见；
  - 在画布上阻止 `gesturestart` 和双指缩放；
  - 检测到微信 UA（`MicroMessenger`）时，在 banner 里提示"建议点右上角 ··· 选择在浏览器打开，体验更稳定"，提示可以关掉，关掉后记住（用 `safeSet`）；
  - 各个按钮的触控区域不小于 44px。
- [ ] **Step 2：手动验证** — 在 iPhone Safari、安卓 Chrome、微信内置浏览器里各打开一次：
  - 键盘不会遮住输入框；
  - 画画时页面不缩放；
  - 切到微信待 10 秒再切回来，能自动重连，分数不变。
- [ ] **Step 3**：achievements + commit `feat: mobile polish`

### Task 17：默认词库、README、真机测试清单

**Files:**
- Create: `words/默认.txt`（约 300 个常见、好画的词：动物、食物、日常物品、动作、地点、职业，一行一个）、`README.md`
- Modify: `tests/server/test_wordbank.py`（加一条测试：仓库里自带的词库至少 200 个词，并且每个词规范化后都非空）

README 内容：

- **启动**：用 `PY main.py`，手机在同一 Wi-Fi 下打开显示的地址；
- **改配置**：改 `config.toml` 后重启服务器；
- **加词库**：把 txt 放进 `words/`，不用重启；GBK 和 UTF-8 编码都支持；
- **部署选项**：
  - 家里电脑做路由器端口转发（以及 Windows 防火墙要放行的端口）；
  - 内网穿透；
  - 境外 VPS（洛杉矶或日本），在上面用 Linux 跑同样的命令，挂在反向代理后面时 WebSocket 会自动走 `wss`；
- **常见问题**：微信打不开时怎么办、国内朋友卡顿时怎么办。

- [ ] **Step 1**：写词库和 README；加上那条测试，跑通。
- [ ] **Step 2**：全部测试通过（`pytest` 和 `node --test`）；achievements + commit `docs: default word bank and README`

**子项目 6 验证：** 用户按 README 让外地朋友实际连进来玩一局（家里电脑或 VPS 都可以）。把遇到的问题记进 achievements.md，**停下等确认**。之后的联想模式另开企划。
