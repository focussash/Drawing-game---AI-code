@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 双击启动游戏服务器（同一 Wi-Fi 下的手机可以玩）。
rem 如果你的 Python 环境不在这个路径，改成你自己的 python.exe。
"E:\MiniConda\envs\biomotum\python.exe" main.py
pause
