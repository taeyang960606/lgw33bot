@echo off
chcp 65001 >nul
title LGW33 Bot - Python Virtual Environment Setup

echo ================================
echo   LGW33 Bot - 虚拟环境初始化
echo ================================

REM 检查 python 是否存在
python --version >nul 2>&1
if errorlevel 1 (
    echo [❌] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b
)

REM 创建虚拟环境
if not exist venv (
    echo [⏳] 正在创建虚拟环境 venv ...
    python -m venv venv
    if errorlevel 1 (
        echo [❌] 虚拟环境创建失败
        pause
        exit /b
    )
    echo [✅] 虚拟环境创建完成
) else (
    echo [ℹ️] 已存在虚拟环境 venv，跳过创建
)

REM 激活虚拟环境
echo [⏳] 激活虚拟环境...
call venv\Scripts\activate

REM 升级 pip
echo [⏳] 升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
if exist requirements.txt (
    echo [⏳] 安装 requirements.txt 依赖...
    pip install -r requirements.txt
) else (
    echo [⚠️] 未找到 requirements.txt，跳过依赖安装
)

echo ================================
echo [🎉] 环境已准备完成！
echo ================================
echo 现在你可以运行：
echo     python app.py
echo.

pause
