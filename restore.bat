@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Restore from Snapshot
REM  Usage:  restore.bat <snapshot-file>
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || ( echo [X] Cannot cd to project & pause & exit /b 1 )

set "SNAP=%~1"

if "%SNAP%"=="" (
    echo Available snapshots:
    echo.
    dir /b /o-d "snapshots\*.zip" 2>nul
    echo.
    set /p "SNAP=Enter snapshot filename: "
)

if not exist "%SNAP%" (
    if exist "snapshots\%SNAP%" (
        set "SNAP=snapshots\%SNAP%"
    ) else (
        echo [X] Snapshot not found: %SNAP%
        pause
        exit /b 1
    )
)

echo ============================================================
echo   Restoring from: %SNAP%
echo ============================================================
echo.

REM ---------- Move current project to safety folder ----------
for /f "tokens=2-4 delims=/ " %%A in ('date /t') do set "D=%%C%%A%%B"
for /f "tokens=1-2 delims=: " %%A in ('time /t') do set "T=%%A%%B"
set "T=%T: =0%"
set "SAFE=_before_restore_%D%_%T%"

echo [1/3] Moving current project to %SAFE% ...
if not exist "%SAFE%" mkdir "%SAFE%"
for %%F in (*.py) do move "%%F" "%SAFE%\" >nul 2>nul
if exist "telecom_sim_output" move "telecom_sim_output" "%SAFE%\" >nul 2>nul

REM ---------- Extract snapshot ----------
echo.
echo [2/3] Extracting snapshot ...
powershell -NoProfile -Command "Expand-Archive -Path '%SNAP%' -DestinationPath '.' -Force"
if errorlevel 1 (
    echo [X] Extraction failed. Rolling back ...
    for %%F in ("%SAFE%\*.py") do move "%%F" "." >nul 2>nul
    if exist "%SAFE%\telecom_sim_output" move "%SAFE%\telecom_sim_output" "." >nul 2>nul
    pause
    exit /b 1
)

REM ---------- Verify ----------
echo.
echo [3/3] Verifying ...
python check_6g_now.py

echo.
echo ============================================================
echo   RESTORE COMPLETE
echo ============================================================
echo   If everything looks good, delete the safety folder:
echo     rmdir /s /q "%SAFE%"
echo.
echo   If you want to roll back:
echo     move "%SAFE%\*.py" .
echo     move "%SAFE%\telecom_sim_output" .
echo ============================================================
echo.
pause
endlocal
