@echo off
REM Prints your Telegram chat id (message your bot first).
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python get_chat_id.py
pause
