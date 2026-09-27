@echo off
REM One-time setup on the Windows RDP. Run from inside the axs-resale-bot folder.
cd /d "%~dp0"
py -3 -m venv .venv || python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
if not exist .env copy .env.example .env
echo.
echo Setup done. Now edit .env (notepad .env), then double-click run.bat
pause
