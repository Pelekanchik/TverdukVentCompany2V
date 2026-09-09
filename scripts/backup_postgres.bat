@echo off
setlocal
cd /d %~dp0..
call .venv\Scripts\activate.bat
python -m ventilation_company.utils.backup
endlocal
