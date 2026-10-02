@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Full Rebuild
REM  Snapshot -> wipe -> regenerate -> restore 2PB -> verify
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || ( echo [X] Cannot cd to project & pause & exit /b 1 )

echo ============================================================
echo   TELECOM-NET-SIM  ^|  Full Rebuild
echo ============================================================
echo.

REM ---------- 1) Snapshot before wipe ----------
if not exist "snapshots" mkdir "snapshots"
for /f "tokens=2-4 delims=/ " %%A in ('date /t') do set "D=%%C%%A%%B"
for /f "tokens=1-2 delims=: " %%A in ('time /t') do set "T=%%A%%B"
set "T=%T: =0%"
set "SNAP=snapshots\pre_rebuild_%D%_%T%.zip"

echo [1/5] Snapshotting to %SNAP% ...
powershell -NoProfile -Command "Compress-Archive -Path '*.py','telecom_sim_output' -DestinationPath '%SNAP%' -Force" >nul 2>nul
if exist "%SNAP%" ( echo       [v] Snapshot created ) else ( echo       [!] Snapshot skipped )

REM ---------- 2) Wipe DB ----------
echo.
echo [2/5] Wiping telecom_sim_output ...
if exist "telecom_sim_output" rmdir /s /q "telecom_sim_output"

REM ---------- 3) Rebuild ----------
echo.
echo [3/5] Running simulator ...
python telecom_net_sim.py
if errorlevel 1 ( echo [X] Simulator failed. & pause & exit /b 1 )

echo.
echo [4/5] Running attack generator ...
python telecom_attack.py
if errorlevel 1 ( echo [X] Attack failed. & pause & exit /b 1 )

echo.
echo [5/5] Restoring 2PB traffic ...
python restore_2pb.py
if errorlevel 1 ( echo [!] restore_2pb failed )

REM ---------- Verify ----------
echo.
echo ============================================================
echo   VERIFY
echo ============================================================
python check_6g_now.py

echo.
echo [OK] Rebuild complete.
echo.
pause
endlocal
