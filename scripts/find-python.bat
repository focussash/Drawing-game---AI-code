@echo off
rem 找到用来运行游戏的 python.exe，结果放进 PY 变量。start-server.bat 和 start-online.bat 会这样调用它：
rem   call scripts\find-python.bat <项目文件夹>
rem 找的顺序：
rem   1. 项目文件夹里的 python-path.txt：第一行写 python.exe 的完整路径（这个文件只在你的电脑上，不进 git）
rem   2. 名为 nhwc 的 conda 环境，也就是 environment.yml 建出来的那个
rem   3. PATH 里的 python
set "PY="
set "NHWC_ROOT=%~1"
set "NHWC_ENV=nhwc"

if not exist "%NHWC_ROOT%python-path.txt" goto :conda
for /f "usebackq delims=" %%L in ("%NHWC_ROOT%python-path.txt") do if not defined PY set "PY=%%~L"
if defined PY goto :check

:conda
rem conda 在 PATH 里时，从 conda 命令的位置推出安装目录（conda.exe 在 Scripts\ 或 condabin\ 或 Library\bin\ 里）
for /f "delims=" %%C in ('where conda 2^>nul') do (
  call :try "%%~dpC..\envs\%NHWC_ENV%\python.exe"
  call :try "%%~dpC..\..\envs\%NHWC_ENV%\python.exe"
)
rem 再看几个常见的安装位置
for %%R in ("%USERPROFILE%\miniconda3" "%USERPROFILE%\anaconda3" "%USERPROFILE%\miniforge3" "%LOCALAPPDATA%\miniconda3" "%ProgramData%\miniconda3" "%ProgramData%\anaconda3" "%USERPROFILE%\.conda") do call :try "%%~R\envs\%NHWC_ENV%\python.exe"
if defined PY goto :check
for /f "delims=" %%P in ('where python 2^>nul') do call :try "%%P"
if not defined PY goto :missing

:check
"%PY%" -c "import fastapi, uvicorn" >nul 2>&1 && exit /b 0
echo 找到的 Python 用不了：%PY%
echo 可能是路径不对，也可能是里面没装 fastapi 和 uvicorn。
goto :help

:missing
echo 没有找到 Python。

:help
echo.
echo 解决办法（详见 README 的「安装」一节）：
echo   1. 装好 Miniconda 后，在这个文件夹里运行：conda env create -f environment.yml
echo   2. 或者在这个文件夹里新建 python-path.txt，只写一行：你的 python.exe 的完整路径
exit /b 1

:try
rem 还没找到、并且这个文件存在，就用它（顺便把 ..\ 化简掉）
if defined PY exit /b 0
if exist "%~1" set "PY=%~f1"
exit /b 0
