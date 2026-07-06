@echo off
cd /d "%~dp0"

if exist "FarmManagementSystem.exe" (
    start "" FarmManagementSystem.exe
) else (
    call .venv\Scripts\activate.bat
    python app.py
)

pause