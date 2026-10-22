"""Start the 你画我猜 server: python main.py [--config config.toml] [--online]"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from server.config import ConfigError, load_config
from server.net.lan import lan_ip
from server.net.tunnel import LOOPBACK, Tunnel
from server.wordbank import list_banks, load_bank

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.toml"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="你画我猜服务器")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="配置文件路径")
    parser.add_argument("--online", action="store_true",
                        help="同时打开临时公网地址（localhost.run），并且只接受隧道转来的连接")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        from server.net.app import create_app  # imported late: config errors should not need FastAPI
        app = create_app(config)
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    if args.online and shutil.which("ssh") is None:
        print("找不到 ssh 命令，无法打开公网地址。Windows 10/11 一般自带；也可以先用 start-server.bat 在局域网里玩。",
              file=sys.stderr)
        raise SystemExit(1)

    host = LOOPBACK if args.online else config.server.host
    _print_banner(config, online=args.online)
    _serve(app, host, config.server.port, args.online)


def _serve(app, host: str, port: int, online: bool) -> None:
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, ws_ping_interval=20,
                                           ws_ping_timeout=20, log_level="warning"))
    tunnel = Tunnel(port) if online else None
    if tunnel:
        def on_tunnel_exit(code: int | None) -> None:
            if server.should_exit:
                return  # we are already shutting down
            print("\n公网地址已断开，游戏服务器也一起关闭。重新双击 start-online.bat 即可（网址会变）。", flush=True)
            server.should_exit = True

        tunnel.start_when_ready(server, on_tunnel_exit)
    try:
        server.run()
    finally:
        if tunnel:
            tunnel.stop()


def _print_banner(config, online: bool = False) -> None:
    # Line-buffered so the banner shows up even when output is piped to a log;
    # errors="replace" so a console that can't show Chinese never crashes startup.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, errors="replace")
    port = config.server.port
    banks = list_banks(config.words_dir)
    print("你画我猜 服务器已启动")
    if online:
        print("  公网模式：只接受公网地址转来的连接，同一网络里的其他人不能直接连。")
        print("  稍等几秒，下面会出现 https://….lhr.life，把它发给朋友（每次都不一样）。")
        print("  拿到网址的任何人都能进来；关掉这个窗口 = 服务器和公网地址一起关闭。")
    else:
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
