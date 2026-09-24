@echo off
chcp 65001 > nul 2>&1
title Death Proxy Scanner - Master Server (Port 5000)
color 0b
echo =====================================================================
echo  DEATH PROXY SCANNER V1.0.0 - MASTER SERVER
echo  Created By ! Death Silence - Discord: @qyk3
echo  Official Server: https://discord.gg/2zuwDpJaNP
echo =====================================================================
echo.
echo [*] Dang kiem tra Python...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python chua duoc cai dat hoac chua them vao PATH!
    pause
    exit /b 1
)

echo [*] Dang cai dat/kiem tra thu vien can thiet...
pip install -q -r requirements.txt

echo [*] Dang khoi dong Master Server...
echo.
python server.py
pause
