@echo off
chcp 65001 >nul
echo ========================================
echo  🧪 VentCompany Test Runner
echo ========================================
echo.

where pytest >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pytest не знайдено. Встановіть:
    echo    pip install pytest pytest-cov
    pause
    exit /b 1
)

echo Запуск тестів...
pytest tests -v --tb=short %*
echo.
pause
