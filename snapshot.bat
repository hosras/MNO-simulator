@echo off
REM TELECOM-NET-SIM | Quick Snapshot (fixed timestamp)
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || ( echo [X] Cannot cd to project & pause & exit /b 1 )

if not exist "snapshots" mkdir "snapshots"

set "TAG=%~1"
if "%TAG%"=="" set "TAG=manual"

REM --- robust timestamp using PowerShell ---
for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%A"

set "SNAP=snapshots\snap_%TAG%_%STAMP%.zip"

echo ============================================================
echo   Creating snapshot: %SNAP%
echo ============================================================

powershell -NoProfile -Command "Compress-Archive -Path '*.py','telecom_sim_output' -DestinationPath '%SNAP%' -Force"

if exist "%SNAP%" (
    echo [OK] Snapshot created.
    for %%F in ("%SNAP%") do echo      Size: %%~zF bytes
) else (
    echo [X] Snapshot failed.
)

echo.
pause
endlocal