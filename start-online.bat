@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 双击：启动游戏服务器 + 通过 localhost.run 打开一个临时公网地址，外地朋友也能进。
rem 免费、不用注册、不用装软件（用 Windows 自带的 ssh）。关掉这个窗口公网地址就失效。
echo 正在新窗口里启动游戏服务器...
start "你画我猜 服务器" "E:\MiniConda\envs\biomotum\python.exe" main.py
timeout /t 3 >nul
echo.
echo 正在申请公网地址。下面出现的 https://....lhr.life 就是发给朋友的网址（每次都不一样）。
echo 注意：拿到网址的任何人都能进来玩；关掉这个窗口就断开。
echo.
ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
echo.
echo 公网地址已断开。服务器窗口要单独关掉。
pause
