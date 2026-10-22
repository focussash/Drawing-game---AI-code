"""One WebSocket with an outgoing queue, so slow clients never block the room."""

from __future__ import annotations

import asyncio
import logging

from starlette.websockets import WebSocket

log = logging.getLogger(__name__)


class Connection:
    def __init__(self, ws: WebSocket):
        self._ws = ws
        self._queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        self.closed = False

    def send(self, text: str) -> None:
        if not self.closed:
            self._queue.put_nowait(("text", text))

    def close(self, code: int) -> None:
        """Close after everything already queued has been sent."""
        if not self.closed:
            self.closed = True
            self._queue.put_nowait(("close", code))

    async def run_writer(self) -> None:
        try:
            while True:
                kind, payload = await self._queue.get()
                if kind == "close":
                    await self._ws.close(code=payload)
                    return
                await self._ws.send_text(payload)
        except Exception:  # socket already gone; the receive loop does the cleanup
            log.debug("writer stopped", exc_info=True)
