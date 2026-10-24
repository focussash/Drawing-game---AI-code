@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 双击启动游戏服务器（同一 Wi-Fi 下的手机可以玩）。
rem 用的是哪个 Python：见 scripts\find-python.bat。
call scripts\find-python.bat "%~dp0"
if errorlevel 1 goto :end
"%PY%" main.py
:end
pause
