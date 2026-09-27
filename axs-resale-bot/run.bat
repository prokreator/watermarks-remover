@echo off
REM Starts the bot and restarts it automatically if it crashes or the RDP drops.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
:loop
python bot.py
echo Bot stopped. Restarting in 15 seconds (close this window to stop for good)...
timeout /t 15 /nobreak >nul
goto loop
