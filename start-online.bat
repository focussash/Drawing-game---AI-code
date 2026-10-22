@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 双击：启动游戏服务器，并打开一个临时公网地址（localhost.run，免费、不用注册、不用装软件）。
rem 公网模式下服务器只接受公网地址转来的连接；关掉这个窗口，服务器和公网地址一起关闭。
"E:\MiniConda\envs\biomotum\python.exe" main.py --online
pause
