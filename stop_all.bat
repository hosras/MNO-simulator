@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Stop all Streamlit apps
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "PORTS=8501 8502 8503"

echo ============================================================
echo   Stopping TELECOM Streamlit apps ...
echo ============================================================

for %%P in (%PORTS%) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
        echo [i] Killing PID %%A on port %%P
        taskkill /F /PID %%A >nul 2>nul
    )
)

echo.
echo [OK] All ports checked.
echo.
pause
endlocal
