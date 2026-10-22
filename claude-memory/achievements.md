# 进度记录（achievements）

分支：`dev`（`main` 上只有文档的初始提交）。测试命令：`"E:/MiniConda/envs/biomotum/python.exe" -m pytest tests -q`，JS：`node --test tests/web/`。

## 子项目 1：骨架与核心容器

### Task 1：项目骨架 + 配置加载 ✅
- 新增：`.gitignore`、`requirements.txt`、`package.json`、`config.toml`、`server/config.py`、`tests/server/test_config.py`；CLAUDE.md 补了 Project Overview / dependencies / Architecture。
- 装进 biomotum 环境：fastapi 0.159.1、uvicorn 0.54.0（含 websockets 17.3）。
- 测试：15 个全部通过（比计划多 3 个：配置文件与 dataclass 默认值一致、`[modes] classic = 3` 报错、TOML 语法错误报错）。
- 偏离计划：`git init` 在执行前的准备阶段就做了（文档先提交到 main，开发在 dev 分支）。另外加了 `server.port` 范围检查。
