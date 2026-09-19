@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 定时语音播报 - 一键打包

echo ============================================================
echo   定时语音播报  一键打包成 Windows exe
echo ------------------------------------------------------------
echo   在任意 Windows 电脑上双击本脚本即可，
echo   无需手动敲命令。打包完成后 exe 在 dist 文件夹里。
echo ============================================================
echo.

REM --- 找 Python ---
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    echo [错误] 没有检测到 Python。
    echo 请先到 https://www.python.org/downloads/ 下载安装 Python 3.8+，
    echo 安装时务必勾选 "Add Python to PATH"。
    pause
    exit /b 1
)
echo [√] 检测到 Python: 
%PY% --version

REM --- 建虚拟环境（避免污染全局）---
if not exist ".venv" (
    echo.
    echo [1/4] 创建虚拟环境 .venv ...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

echo.
echo [2/4] 安装依赖（首次需要联网，约 1~2 分钟）...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
)

echo.
echo [3/4] 开始打包（首次较慢，约 2~5 分钟）...
pyinstaller --noconfirm --clean --windowed --onefile ^
  --name "定时语音播报" ^
  --collect-all pyttsx3 ^
  main.py
if errorlevel 1 (
    echo [错误] 打包失败，请把上面红色错误截图反馈
    pause
    exit /b 1
)

echo.
echo [4/4] 完成！
echo ------------------------------------------------------------
echo  可执行文件:  %~dp0dist\定时语音播报.exe
echo.
echo  下一步：
echo   1. 把 "dist\定时语音播报.exe" 拷贝到 U 盘
echo   2. 拷到希沃电脑任意位置（建议桌面）
echo   3. 双击运行，无需安装 Python
echo   4. 首次运行如被 SmartScreen 拦截，点"更多信息" - "仍要运行"
echo ------------------------------------------------------------
pause
endlocal
