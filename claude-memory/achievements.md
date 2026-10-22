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
