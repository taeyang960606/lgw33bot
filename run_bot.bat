@echo off
chcp 65001 >nul
title LGW33 Bot - Telegram Bot Service
echo ================================
echo   LGW33 Bot - 启动中...
echo ================================
echo.

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    echo [✓] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [!] 未找到虚拟环境，使用全局 Python
)

echo [✓] 启动 Bot 服务...
echo.
set PYTHONUTF8=1
python -m bot.main

if errorlevel 1 (
    echo.
    echo [✗] Bot 启动失败！
    pause
) else (
    echo.
    echo [✓] Bot 已停止
    pause
)
