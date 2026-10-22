# 进度记录（achievements）

分支：`dev`（`main` 上只有文档的初始提交）。测试命令：`"E:/MiniConda/envs/biomotum/python.exe" -m pytest tests -q`，JS：`node --test "tests/web/*.test.js"`。

## 子项目 1：骨架与核心容器

### Task 1：项目骨架 + 配置加载 ✅
- 新增：`.gitignore`、`requirements.txt`、`package.json`、`config.toml`、`server/config.py`、`tests/server/test_config.py`；CLAUDE.md 补了 Project Overview / dependencies / Architecture。
- 装进 biomotum 环境：fastapi 0.159.1、uvicorn 0.54.0（含 websockets 17.3）。
- 测试：15 个全部通过（比计划多 3 个：配置文件与 dataclass 默认值一致、`[modes] classic = 3` 报错、TOML 语法错误报错）。
- 偏离计划：`git init` 在执行前的准备阶段就做了（文档先提交到 main，开发在 dev 分支）。另外加了 `server.port` 范围检查。

### Task 2：文本规范化 + 词库 ✅
- 新增：`server/textnorm.py`（normalize / word_length / mask）、`server/wordbank.py`（list_banks / load_bank / load_banks / WordPool）及对应测试。
- 词库读取：先按 UTF-8（带不带 BOM 都行）读，失败再按 GB18030（兼容 GBK）读；`#` 开头的行是注释；重复的词去掉；只能读 `words/` 里真实存在的 txt（防止路径穿越）。
- 测试：13 个（比计划多 3 个：emoji/符号被去掉、目录不存在时返回空、`.size`）。累计 28 个。

### Task 3：核心状态容器 ✅
- 新增：`server/clock.py`、`audience.py`、`players.py`、`chatlog.py`、`canvas_log.py`、`protocol_limits.py`、`msgparse.py`；测试辅助 `tests/server/fakes.py`（FakeClock）；测试 `test_players.py`、`test_containers.py`、`test_msgparse.py`。
- 测试：15 个。累计 43 个。
- 偏离计划：`CanvasLog.begin` 返回 bool（画布点数超上限时返回 False），这样房间可以不转发被丢弃的笔画。

**子项目 1 验证：** `pytest tests` 43/43 通过。按用户指示直接进入子项目 2。

## 子项目 2：经典模式与房间

### Task 4：模式框架与经典模式设置项 ✅
- 新增：`server/modes/__init__.py`（MODES 注册表、parse_mode_configs）、`server/modes/base.py`（SettingSpec、validate_settings、ModeContext、Mode 基类）、`server/modes/classic/settings.py`（ClassicConfig、ScoringConfig、设置项表）、`tests/server/test_settings.py`。
- 等待界面的设置项用一张表定义（key、中文标签、类型、范围），前端以后按这张表自动生成表单，新模式只要提供自己的表。
- 测试：17 个。累计 60 个。

### Task 5：经典模式纯逻辑单元 ✅
- 新增：`server/modes/classic/scoring.py`、`turn_timer.py`、`hints.py`、`judge.py`、`rotation.py`，测试 `tests/server/test_classic_units.py`。
- 计分：猜对得 `round(max(20, 100 × 剩余/总时长) × 0.75^揭字数)`，画手每有一人猜对得 `round(25 × 0.75^揭字数)`（参数都来自配置）。
- 测试：18 个。累计 78 个。

### Task 6：经典模式状态机 ✅
- 新增：`server/modes/classic/mode.py`（ClassicMode），测试辅助 `tests/server/helpers.py`（FakeContext、make_game），测试 `tests/server/test_classic_mode.py`；`server/modes/__init__.py` 注册了 classic。
- 覆盖的场景：选词（手动/超时自动）、猜对（打码、加分、只有知情者能看到后续发言）、猜错公开、首个猜对后缩短倒计时、全员猜对提前结束、时间到、揭字打折、揭字上限、加时上限、房主跳过、画手掉线 15 秒跳过、掉线的人轮到时跳过、短暂掉线不结束整局、打满圈数结束并排名、中途加入、被踢的画手/猜词者、快照不泄露答案、同一局不重复出词。
- 测试：30 个。累计 108 个。
- 小补充：揭字时聊天栏会出现一条系统消息"画手揭示了一个字"；加时会出现"画手加时 10 秒"。

### Task 7：房间 ✅
- 新增：`server/room.py`（Room、JoinError）、`server/room_lobby.py`（LobbyState）、`server/room_context.py`（RoomModeContext）、`server/room_strokes.py`（笔画消息校验）、`server/registry.py`（RoomRegistry，4 位房间码，不含 I/L/O/0/1）、`tests/server/test_room.py`。
- 实现了：加入/凭令牌重连/重名/满员/被踢后进不来；房主改设置、开始游戏（检查人数和词库）、踢人；房主离开 60 秒后自动转交；等待界面里离开的人被清掉，游戏中保留；只有画手能画，颜色/粗细/坐标都校验；畸形消息一律回 error、不抛异常；游戏结束回到等待界面并带上排名；没人在线 10 分钟后房间可回收。
- 测试：38 个。累计 146 个。
- 偏离计划：多拆了一个 `server/room_strokes.py`，让 room.py 不超过 300 行；`welcome` 总是排在给这个人的其他消息前面。

**子项目 2 验证：** `pytest tests` 146/146 通过。测试里完整模拟过的一局：选词 → 作画 → 猜对（打码）→ 揭字打折 → 加时 → 画手掉线跳过 → 打满圈数 → 回到等待界面并显示排名。直接进入子项目 3。

## 子项目 3：网络层

### Task 8：连接、房间驱动、应用 ✅
- 新增：`server/net/connection.py`（每个连接一个发送队列）、`runner.py`（每个房间一个驱动循环：到截止时间或有新消息就 tick 并发送）、`session.py`（hello 握手 → 收发循环）、`app.py`（create_app：首页、房间页、建房 API、WebSocket、静态文件）；占位页 `web/index.html`、`web/room.html`；`pytest.ini`；测试 `tests/server/test_app.py`。
- 断线重连竞态（Review Focus 第 1 条）：只有"当前绑定的连接"断开才算掉线。做了变异检查：故意去掉这个保护后，`test_stale_close_does_not_mark_offline` 会失败，恢复后通过。
- 所有页面都带 `Cache-Control: no-cache`，服务器更新后大家刷新就能拿到新版本。房间码大小写都认。
- 测试：13 个。累计 159 个。
- 备注：Starlette 提示其 TestClient 用 httpx 已过时（建议换 httpx2），只影响测试工具，已在 `pytest.ini` 里屏蔽该提示，没有装新包。

### Task 9：启动入口 ✅
- 新增：`main.py`（`--config` 参数；配置有错时打印出错的键名并退出）、`server/net/lan.py`（局域网 IP）、`tests/server/test_main.py`。
- 启动时会打印本机地址、同一 Wi-Fi 下的手机地址，以及每个词库的词数；没有词库时给出警告。
- 冒烟测试：真实启动服务器，首页返回 200，`POST /api/rooms` 返回了房间码 `K922`，响应头带 no-cache。发现启动信息在输出被重定向时不显示（缓冲问题），已改成按行刷新，并且遇到不能显示的字符时不会崩溃。
- 测试：5 个。累计 164 个。

**子项目 3 验证：** `pytest` 164/164 通过；服务器能启动、能建房。直接进入子项目 4。

## 子项目 4：前端基础

### Task 10：界面草图 ✅（已发给用户过目，不阻塞）
- 草图位置：会话 scratchpad 里的 `mockup.html`（不进仓库）。
- 定下的视觉方向——"作业本"：
  - 底色是方格纸 `#f6faf7`，格线薄荷绿 `#cfe3d8`；
  - 字用蓝黑墨水色 `#1f2a44`；
  - 猜对用老师批改的红笔色 `#d6342c` 打勾；
  - 荧光笔黄 `#ffe066` 表示当前选中。
- 最醒目的一处：提示用田字格加楷体（系统自带的 Kaiti/STKaiti/KaiTi），揭开的字用红色写在格子里。
- 字体只用系统字体：楷体用于提示、房间码和标题，正文用苹方/微软雅黑/Noto Sans。
- 手机竖屏从上到下：
  1. 顶栏（圈数、田字格、倒计时，剩 10 秒内变红）；
  2. 4:3 画布；
  3. 工具栏（只有画手能看到）；
  4. "+10 秒"和"跳过"按钮；
  5. 横向滚动的玩家条（✎ 表示画手，红 ✓ 表示已猜对，掉线的变灰）；
  6. 聊天；
  7. 底部输入框。
- 电脑宽屏：画布在左边，玩家和聊天在右边一栏。

### Task 11：前端纯逻辑 ✅
- 新增：`web/js/lib/storage.js`（不会抛异常的 localStorage）、`web/js/state/reducers.js`（房间页状态）、`web/js/modes/index.js`（前端模式注册表）、`web/js/modes/classic/reducer.js`、`web/js/modes/classic/format.js`；测试 `tests/web/storage.test.js`、`reducers.test.js`、`classic.test.js`。
- 收到 welcome 之前的消息一律忽略；倒计时按"本地收到时间 + 剩余毫秒"算出本地截止时间，不受各地时钟误差影响。
- 测试：JS 21 个（Python 仍是 164 个）。
- 偏离计划：JS 测试命令改成 `node --test "tests/web/*.test.js"`。Node 24 直接传目录会把目录当成文件来跑。

### Task 12：首页、连接、等待界面、聊天 ✅
- 新增/替换：
  - 页面和样式：`web/index.html`、`web/room.html`、`web/css/base.css`、`web/css/home.css`、`web/css/room.css`；
  - 入口和基础：`web/js/home.js`、`web/js/room.js`、`web/js/lib/dom.js`、`web/js/state/store.js`、`web/js/net/socket.js`；
  - 界面模块：`web/js/ui/nickname.js`、`toast.js`、`status.js`、`players.js`、`lobby.js`、`chat.js`；
  - 测试：`tests/web/plumbing.test.js`。
- 提前写好了默认词库 `words/默认.txt`（304 个词，分动物、食物、物品、自然与地点、人物、动作、成语几类），方便手动测试；原计划放在 Task 17。
- 在 Chrome 里手动验证通过：
  - 首页建房；输入昵称后进房；重名自动变"小王2"；
  - 刷新页面后回到原位置，不再问昵称；
  - 聊天两边互通；房主改设置，另一边实时同步，非房主的控件是禁用的；
  - 房主掉线 60 秒后房主转给下一个人，掉线的人从等待界面移除；
  - 踢人后被踢的一方显示"你被房主移出了房间"，再刷新显示"你已被房主移出这个房间"；
  - 服务器停掉时显示"连接断开了，正在重新连接…"，重启后提示"房间不存在"；
  - 控制台没有报错。
- 测到并修掉的问题：等待界面里多出一个"null"字样（replaceChildren 会把 null 当文字）。
- 测试方法备注：同一浏览器的多个标签页共享 localStorage，会互相顶替身份。测多人时用 `localhost` 和 `127.0.0.1` 两个地址，它们的存储是分开的。
- 测试：JS 23 个，Python 164 个。
- 偏离计划：多了 `ui/toast.js`、`ui/status.js`、`css/home.css`；大厅里的玩家列表由 players.js 提供，游戏中的计分条交给模式界面（Task 15），这样核心不需要知道分数。

**子项目 4 验证（用户试玩）：** 用户在手机上试过建房、进房、聊天、改设置，都正常。切到后台再回来还没测：用户说安卓切后台一般不会立刻断开，主要看内存够不够，留到能完整玩一局时再一起测。用户确认继续。

## 子项目 5：画布与经典模式界面

### Task 13：画布纯逻辑 ✅
- 新增：`web/js/canvas/geometry.js`（屏幕坐标 → 1600×1200 逻辑坐标、算出 4:3 的最大尺寸）、`web/js/canvas/batcher.js`（笔画打包：开始一笔立即发，后续的点攒起来批量发，每条消息最多 200 个点，重复的点丢掉）；测试 `tests/web/canvas.test.js`。
- 测试：JS 30 个。

### Task 14：画布渲染、输入、工具栏 ✅（手动验证并入 Task 15）
- 新增：
  - `web/js/canvas/renderer.js`：按逻辑坐标画，支持高分屏，窗口变化时整幅重画；
  - `web/js/canvas/input.js`：手指、笔、鼠标统一处理，只认第一根手指；本地立即画出来，每 40ms 发一次点；禁止 iOS 双指缩放；
  - `web/js/ui/toolbar.js`：7 色、粗细档位、橡皮、清空前确认；
  - `web/js/canvas/board.js`：把上面几样和服务器的笔画消息接起来；能不能画由当前模式决定。
- 修改：`web/js/room.js`（挂载画板）、`web/css/room.css`（工具栏样式；画布按屏幕高度自适应）。
- 两个细节：
  - 笔画编号从随机数开始，画手中途刷新也不会覆盖已有的笔画；
  - 一轮在画到一半时结束，剩下的点直接丢掉，不再发给服务器，免得弹出报错。
- 测试：JS 32 个。
- 偏离计划：多了 `canvas/board.js`；Task 14 的手动验证需要 Task 15 的"轮到谁画"，所以并到 Task 15 一起做。

### Task 15：经典模式界面 ✅（含 Task 14 的手动验证）
- 新增：`web/js/modes/classic/view.js`（顶栏圈数/田字格/倒计时、选词浮层、本轮结果浮层、加时和跳过按钮、计分条、聊天框提示语）、`web/js/modes/classic/selectors.js`（纯逻辑：谁能画、每个田字格显示什么、提示语、计分条、本轮加分）、`web/css/classic.css`（模式自己的样式，加载模式时才挂上）；测试 `tests/web/classic-selectors.test.js`。
- 修 bug：服务器的 `phase` 消息补上 `extends_left`，否则画手一开始就看到"加时次数用完了"（先写了 Python 和 JS 各一条失败测试）。
- 修布局：工具栏在 390px 宽的手机上放不下，改成两行（颜色一行，粗细、橡皮、清空一行）。
- 在 Chrome 里两个身份完整走过：
  - 开局 → 画手看到 3 个候选词，对方看到"正在选词"；
  - 画手画画，对方实时看到；
  - 揭示「电」后对方看到红色的字；加时有系统消息；
  - 猜错的话公开显示；猜对显示「猜对了！✓ **」，按揭字打折计分（74 / 19）；唯一的猜词者猜对后这一轮提前结束，浮层公布答案和加分；
  - 选词超时自动选词；画手离开 15 秒后跳过这一轮（"画手离开了"）；
  - 离开的人回来后直接回到游戏，分数和聊天都在；
  - 房主连跳 4 轮把游戏打完 → 回到等待界面，显示"上一局排名"；
  - 手机尺寸（390×780）下布局正常；画手中途刷新后能接着画；
  - 控制台没有报错。
- 测试：Python 164 个，JS 55 个。
- 已知小问题（不影响玩）：本机多开标签页测试时，同一个地址的标签页会互相顶替身份，这是设计如此（一个人只能在一处在线）。

**子项目 5 验证：** 自动测试全绿 + 浏览器完整走一局通过。等用户用手机实际玩一局。

## 子项目 6：手机打磨与部署

### Task 16：手机体验与微信提示 ✅（真机验证待用户）
- 新增：`web/js/ui/banner.js`（在微信里打开时提示"点右上角「···」选「在浏览器打开」"，可以关掉，关掉后记住）、`web/js/ui/viewport.js`（跟踪手机实际可见区域的高度，键盘弹出时游戏画面跟着缩，输入框不被挡住）；测试 `tests/web/banner.test.js`。
- 修改：
  - 游戏中整个界面固定在可见区域内，画布按可见高度缩放；
  - 全局禁止双击放大（`touch-action: manipulation`）；
  - 首页也加了微信提示。
- 浏览器验证：手机尺寸下页面正常；可见高度能正确读到；非微信环境下不显示提示；没有报错。iOS 键盘、刘海屏、微信内置浏览器需要真机试。
- 偏离计划：工具栏的颜色和粗细按钮是 32–34px，没到 44px（到 44px 的话工具栏要占三行），每个按钮之间留了 6px 间距弥补。
- 测试：JS 45 个，Python 164 个。

### Task 17：默认词库、README、启动脚本 ✅
- 新增：`README.md`（中文：家里怎么玩、外地朋友怎么连（三种方案）、改配置、加词库、常见问题、开发说明）、`start-server.bat`（双击启动）、`start-online.bat`（双击启动 + localhost.run 临时公网地址）、`deploy/nhwc.service`（VPS 上的 systemd 服务）；`config.toml` 每一项都补了中文注释；`tests/server/test_wordbank.py` 加了"自带词库至少 200 词且都有效"的测试。
- 公网隧道没有实测：我尝试用 ssh 连 localhost.run 测试，被 Claude Code 自动模式的安全规则拦下（"对外开放入口"需要用户本人决定）。所以 `start-online.bat` 留给用户自己决定是否运行；README 里写明了它未经实测。
- 踩坑：用 bash 的 printf 写 bat 文件时，路径里的 `\e`、`\b` 被当成转义字符，已改用 Python 原样写入，并检查过。
- 测试：Python 165 个，JS 45 个。

**子项目 6 验证：** 自动测试 Python 165 / JS 45 全绿。手机真机打磨效果和公网访问需要用户测试。

## 收尾
- 全分支自审（Review Focus 五条每条都有对应的测试；重点检查了断线和重连的顺序、游戏结束的调用链、截止时间过后会不会空转、客户端残留的旧连接、揭字下标在 Python 和 JS 中是否一致）：没有必须修的问题。
- 记下的小问题（暂不处理）：
  - 建房和聊天没有频率限制（朋友之间用，没人在的房间 10 分钟后会回收）；
  - iOS 键盘处理和微信内置浏览器只在电脑浏览器里验证过；
  - 画布笔画超过 10 万个点之后，画手本地还能画，但不会再转发给别人；
  - `start-online.bat` 的公网隧道没有实测。
- 代码在 `dev` 分支上（18 个提交），还没合并到 `main`，等用户决定。

## 修复：公网隧道返回 502 "no tunnel"（2026-10-22）
- 现象：用户在学校网络下运行 `start-online.bat`，拿到了 `https://….lhr.life`，打开后提示 "no tunnel"。同一 Wi-Fi 下用局域网 IP 访问是正常的。
- 排查：
  - 服务器在监听 `0.0.0.0:8000`；ssh 进程活着，和 localhost.run 保持着连接；
  - 从本机 curl 那个网址，复现出 `502 Bad Gateway / no tunnel`。502 说明 localhost.run 认得这个网址，但转回本机时失败；
  - 在本机上，`localhost` 先解析成 `::1`，连 `::1:8000` 被拒绝，连 `127.0.0.1:8000` 正常。
- 根因：隧道写的是转发到 `localhost:8000`，ssh 去连 IPv6 的 `::1`，而服务器只监听 IPv4。
- 修复：`start-online.bat` 改成转发到 `127.0.0.1:8000`；README 里 Caddy 的示例也改成 `127.0.0.1:8000`；新增回归测试 `tests/server/test_scripts.py`（修复前失败、修复后通过）。Python 测试 166 个。
- 待用户确认：重新运行脚本后，新网址能不能打开。
