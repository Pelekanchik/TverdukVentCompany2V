@echo off
setlocal
cd /d %~dp0..
call .venv\Scripts\activate.bat
python -m alembic upgrade head
if errorlevel 1 exit /b 1
python launch_gui.py
endlocal
