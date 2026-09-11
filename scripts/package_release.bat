@echo off
setlocal
cd /d %~dp0..

if not exist dist\VentCompany (
    echo Build dist\VentCompany first: scripts\build_installer.bat
    exit /b 1
)

set VERSION=%1
if "%VERSION%"=="" set VERSION=0.1.0

if not exist release mkdir release

powershell -NoProfile -Command "Compress-Archive -Path 'dist\VentCompany\*' -DestinationPath 'release\VentCompany-v%VERSION%.zip' -Force"

echo.
echo Release package created:
echo   release\VentCompany-v%VERSION%.zip
endlocal
