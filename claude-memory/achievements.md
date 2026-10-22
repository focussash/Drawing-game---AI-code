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
