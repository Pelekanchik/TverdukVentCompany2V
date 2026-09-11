@echo off
setlocal
cd /d %~dp0..
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements-build.txt
pyinstaller --clean --noconfirm VentCompany.spec

echo.
echo Build finished: dist\VentCompany
endlocal
