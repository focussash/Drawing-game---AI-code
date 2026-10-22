"""Protocol-level limits and WebSocket close codes (not game rules)."""

MAX_POINTS_PER_MESSAGE = 400  # flat [x, y, ...] length, i.e. 200 points
HELLO_TIMEOUT_SECONDS = 10

CLOSE_HANDSHAKE_FAILED = 4000
CLOSE_REPLACED = 4001
CLOSE_KICKED = 4003
CLOSE_ROOM_NOT_FOUND = 4004
