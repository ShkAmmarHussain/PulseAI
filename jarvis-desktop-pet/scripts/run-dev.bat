# Start backend and Tauri UI
@echo off
setlocal
cd /d %~dp0

REM Backend
start "jarvis-backend" cmd /k "cd /d %~dp0 && python backend\main.py"

REM Tauri UI (dev)
start "jarvis-ui" cmd /k "cd /d %~dp0\ui_pet && npm run tauri dev"
endlocal
