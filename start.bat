@echo off
chcp 65001 > nul
title Smart Home & Family Task Hub
echo ========================================================
echo   Smart Home & Family Task Hub (Семейный органайзер)
echo ========================================================
echo [INFO] Запуск семейного сервера на http://localhost:8003 ...
start http://localhost:8003
python -m uvicorn main:app --host 0.0.0.0 --port 8003
pause
