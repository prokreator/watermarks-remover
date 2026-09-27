@echo off
REM Checks the Telegram setup and sends a test notification to your phone.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python test_telegram.py
pause
