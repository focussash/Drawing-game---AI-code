# 进度记录（achievements）

分支：`dev`（`main` 上只有文档的初始提交）。测试命令：`"E:/MiniConda/envs/biomotum/python.exe" -m pytest tests -q`，JS：`node --test tests/web/`。

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
