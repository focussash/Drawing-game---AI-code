"""Start the 你画我猜 server: python main.py [--config config.toml]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from server.config import ConfigError, load_config
from server.net.lan import lan_ip
from server.wordbank import list_banks, load_bank

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.toml"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="你画我猜服务器")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="配置文件路径")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        from server.net.app import create_app  # imported late: config errors should not need FastAPI
        app = create_app(config)
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    _print_banner(config)
    import uvicorn

    uvicorn.run(app, host=config.server.host, port=config.server.port,
                ws_ping_interval=20, ws_ping_timeout=20, log_level="warning")


def _print_banner(config) -> None:
    # Line-buffered so the banner shows up even when output is piped to a log;
    # errors="replace" so a console that can't show Chinese never crashes startup.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, errors="replace")
    port = config.server.port
    banks = list_banks(config.words_dir)
    print("你画我猜 服务器已启动")
    print(f"  本机打开:      http://localhost:{port}")
    ip = lan_ip()
    if ip:
        print(f"  同一 Wi-Fi 下: http://{ip}:{port}")
    if banks:
        summary = "、".join(f"{b}({len(load_bank(config.words_dir, b))})" for b in banks)
        print(f"  词库: {summary}")
    else:
        print(f"  警告: {config.words_dir} 里没有任何 .txt 词库，开始游戏前请先放一个进去")
    print("  按 Ctrl+C 停止")


if __name__ == "__main__":
    main()
