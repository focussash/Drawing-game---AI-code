"""FastAPI app: pages, static files, room creation and the WebSocket endpoint."""

from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.clock import Clock, SystemClock
from server.config import AppConfig
from server.net.runner import RoomRunner
from server.net.session import run_session
from server.registry import RoomRegistry

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def create_app(config: AppConfig, clock: Clock | None = None, rng: random.Random | None = None,
               web_dir: Path = WEB_DIR) -> FastAPI:
    clock = clock or SystemClock()
    registry = RoomRegistry(config, clock, rng or random.Random())
    runners: dict[str, RoomRunner] = {}
    tasks: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        for task in tasks:
            task.cancel()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.registry = registry
    app.state.runners = runners

    @app.middleware("http")
    async def no_cache(request, call_next):
        # Always revalidate, so everyone gets the new pages after the server restarts.
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/")
    async def home() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    @app.get("/r/{code}")
    async def room_page(code: str) -> FileResponse:
        return FileResponse(web_dir / "room.html")

    @app.post("/api/rooms")
    async def create_room() -> dict:
        room = registry.create()
        code = room.code

        def on_done() -> None:
            registry.remove(code)
            runners.pop(code, None)

        runner = RoomRunner(room, clock, on_done)
        runners[code] = runner
        task = asyncio.create_task(runner.run())
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return {"code": code}

    @app.websocket("/ws/{code}")
    async def ws_endpoint(ws: WebSocket, code: str) -> None:
        await run_session(ws, code.upper(), registry, runners)

    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app
