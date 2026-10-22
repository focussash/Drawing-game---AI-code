# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Important**: Always check the `claude-memory/` folder for project context, plans, and progress tracking before starting any work.

## Development Guidelines

- **Follow the plan**: Always refer to `DEVELOPMENT_PLAN.md` before writing any code. The plan defines the implementation order and specifications.
- **Plan changes require approval**: Even with auto-accept enabled, **you MUST ask the user for explicit permission** before modifying DEVELOPMENT_PLAN.md. Never silently iterate on the plan.
- **Modularity is mandatory**: Avoid monolith code at all costs. Split functionality into small, focused modules. Each file should have a single responsibility.

### Progress Tracking (CRITICAL)

- **After EVERY substep**: Update `achievements.md` immediately with what was accomplished. Do not wait until a full subproject is complete.
- **Re-read claude-memory/ after every step**: Before starting any new work, re-read `DEVELOPMENT_PLAN.md` and `achievements.md` to ensure you are still aligned with the plan and aware of current progress.
- **One subproject at a time**: Complete and validate one subproject before moving to the next. Stop after validation and wait for user confirmation before proceeding.
- **Validation before proceeding**: After implementing a subproject, run tests and show results to the user. Do not proceed until validation passes.
- **Document everything**: Include test counts, file changes, any deviations from the plan (e.g., using `cnlunar` instead of `sxtwl`), and any issues encountered.

## Project Overview

A browser-based 你画我猜 (Pictionary) game for a group of friends spread across US East, US Central and China. Mobile browsers first. Spec: `claude-memory/DESIGN.md`; plan: `claude-memory/DEVELOPMENT_PLAN.md`; progress: `claude-memory/achievements.md`.

Run JS tests with `node --test "tests/web/*.test.js"` (Node built-in runner; no npm packages; the bare directory form does not work on Node 24).

## Environment

**CRITICAL**: This project uses a MiniConda virtual environment. **NEVER** install packages into native Python.

```
Virtual env: E:\MiniConda\envs\biomotum
Python:      3.13.1
```

All commands MUST use the full venv Python path:
```bash
# Run the application
"E:\MiniConda\envs\biomotum\python.exe" main.py

# Install dependencies (INTO VENV ONLY)
"E:\MiniConda\envs\biomotum\python.exe" -m pip install <package>

# Run tests
"E:\MiniConda\envs\biomotum\python.exe" -m pytest tests/ -v
```

**Current dependencies**: fastapi, uvicorn[standard] (runtime); pytest, httpx (tests). See `requirements.txt`.

## Permissions

- **Bash**: You may run ALL bash commands freely (dangerously skip permissions) **UNLESS** you are deleting files/folders or installing non-Python things. Tests, pip installs into venv, running the app, git commands, etc. are all fine without asking.
- **File edits**: Proceed freely for implementation work.

## Architecture

### Current Structure

- `config.toml` — all tunables (server, room, drawing, per-mode defaults). Loaded by `server/config.py`.
- `words/*.txt` — word banks, one word per line (UTF-8 or GBK).
- `server/` — Python backend. Game rules are pure logic (no network, injected clock); `server/modes/<name>/` holds each game mode; `server/net/` is the FastAPI/WebSocket layer.
- `web/` — zero-build frontend (HTML/CSS/ES modules).
- `tests/server/` (pytest), `tests/web/` (`node --test "tests/web/*.test.js"`).