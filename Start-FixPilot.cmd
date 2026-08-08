@echo off
setlocal
cd /d "%~dp0backend"
title FixPilot Local Server
echo.
echo FixPilot is starting at http://127.0.0.1:8000
echo Keep this window open while using FixPilot.
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
  echo.
  echo FixPilot could not start. Copy the error above and send it to Codex.
)
pause
