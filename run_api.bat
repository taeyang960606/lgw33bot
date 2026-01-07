@echo off
chcp 65001 >nul
title LGW33 Bot - API Service
echo ================================
echo   LGW33 Bot - API 启动中...
echo ================================
echo.

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    echo [✓] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [!] 未找到虚拟环境，使用全局 Python
)

echo [✓] 启动 API 服务 (http://127.0.0.1:8000)
echo.
set PYTHONUTF8=1
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

if errorlevel 1 (
    echo.
    echo [✗] API 启动失败！
    pause
) else (
    echo.
    echo [✓] API 已停止
    pause
)
