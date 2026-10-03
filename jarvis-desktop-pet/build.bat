@echo off
set TEMP=D:\Personal_projects\2\Personal_AI\temp_build
set TMP=D:\Personal_projects\2\Personal_AI\temp_build
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set PATH=%USERPROFILE%\.cargo\bin;%PATH%
cd /d D:\Personal_projects\2\Personal_AI\jarvis-desktop-pet\ui_pet
call npm run tauri build > ..\..\build_log.txt 2>&1
if errorlevel 1 (echo BUILD_FAILED >> ..\..\build_log.txt) else (echo BUILD_OK >> ..\..\build_log.txt)