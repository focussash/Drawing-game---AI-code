"""One WebSocket's life: hello handshake, then relay messages into the room."""

from __future__ import annotations

import asyncio
import json
import logging

from starlette.websockets import WebSocket, WebSocketDisconnect

from server.net.connection import Connection
from server.net.runner import RoomRunner
from server.protocol_limits import (
    CLOSE_HANDSHAKE_FAILED,
    CLOSE_REPLACED,
    CLOSE_ROOM_NOT_FOUND,
    HELLO_TIMEOUT_SECONDS,
)
from server.registry import RoomRegistry
from server.room import JoinError

log = logging.getLogger(__name__)

PONG = json.dumps({"type": "pong"})
_ERROR_TEXT = {
    "room_not_found": "房间不存在",
    "room_full": "房间已满",
    "banned": "你已被房主移出这个房间",
    "need_nickname": "请先输入昵称",
    "bad_nickname": "昵称不能为空",
    "bad_message": "第一条消息必须是 hello",
}
_DISCONNECTED = (WebSocketDisconnect, RuntimeError, KeyError)


async def run_session(ws: WebSocket, code: str, registry: RoomRegistry, runners: dict[str, RoomRunner]) -> None:
    await ws.accept()
    room, runner = registry.get(code), runners.get(code)
    if room is None or runner is None:
        return await _reject(ws, "room_not_found", CLOSE_ROOM_NOT_FOUND)

    hello = await _receive_hello(ws)
    if hello is None:
        return await _reject(ws, "bad_message", CLOSE_HANDSHAKE_FAILED)
    token = hello.get("token") if isinstance(hello.get("token"), str) else None
    try:
        player = room.join(token, hello.get("nickname"))
    except JoinError as e:
        return await _reject(ws, e.code, CLOSE_HANDSHAKE_FAILED)

    conn = Connection(ws)
    writer = asyncio.create_task(conn.run_writer())
    replaced = runner.bind(player.id, conn)
    if replaced is not None:
        replaced.close(CLOSE_REPLACED)
    room.connect(player.id)
    runner.flush()
    runner.poke()
    try:
        await _receive_loop(ws, conn, runner, player.id)
    finally:
        # Only the player's current connection may mark them offline; a
        # replaced connection closing late must not undo a reconnect.
        if runner.unbind(player.id, conn):
            room.disconnect(player.id)
            runner.flush()
            runner.poke()
        conn.close(CLOSE_HANDSHAKE_FAILED)
        await asyncio.wait([writer], timeout=1)


async def _receive_hello(ws: WebSocket) -> dict | None:
    try:
        text = await asyncio.wait_for(ws.receive_text(), HELLO_TIMEOUT_SECONDS)
        msg = json.loads(text)
    except (TimeoutError, ValueError, *_DISCONNECTED):
        return None
    if not isinstance(msg, dict) or msg.get("type") != "hello":
        return None
    return msg


async def _receive_loop(ws: WebSocket, conn: Connection, runner: RoomRunner, pid: str) -> None:
    try:
        while True:
            text = await ws.receive_text()
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("type") == "ping":
                conn.send(PONG)
                continue
            runner.room.handle(pid, msg)
            runner.flush()
            runner.poke()
    except _DISCONNECTED:
        return


async def _reject(ws: WebSocket, code: str, close_code: int) -> None:
    try:
        await ws.send_json({"type": "error", "code": code, "message": _ERROR_TEXT.get(code, code)})
        await ws.close(code=close_code)
    except Exception:
        log.debug("reject failed", exc_info=True)
