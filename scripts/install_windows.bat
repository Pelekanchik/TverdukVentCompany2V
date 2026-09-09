@echo off
setlocal
cd /d %~dp0..

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo Created .env from .env.example
    echo EDIT .env BEFORE running migrations/app!
) else (
    echo .env already exists
)

echo.
echo Next steps:
echo   1. Edit .env
echo   2. .venv\Scripts\python -m alembic upgrade head
echo   3. scripts\run_app.bat
endlocal
