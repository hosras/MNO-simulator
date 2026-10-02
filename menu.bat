@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Main Menu
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul
set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || ( echo [X] Cannot cd to project & pause & exit /b 1 )

:MENU
cls
echo ============================================================
echo   TELECOM-NET-SIM  ^|  Main Menu
echo ============================================================
echo.
echo   [1]  Run all apps (dashboard + radar + admin)
echo   [2]  Stop all apps
echo   [3]  Rebuild database from scratch
echo   [4]  Take snapshot
echo   [5]  Restore from snapshot
echo   [6]  Health check (check_db + check_6g_now)
echo   [7]  Restore 2PB traffic
echo   [8]  Reset admin password
echo   [0]  Exit
echo.
set /p "CH=Select option: "

if "%CH%"=="1" start "" run_all.bat
if "%CH%"=="2" call stop_all.bat & goto MENU
if "%CH%"=="3" call rebuild.bat & goto MENU
if "%CH%"=="4" call snapshot.bat & goto MENU
if "%CH%"=="5" call restore.bat & goto MENU
if "%CH%"=="6" (
    python check_db.py
    echo.
    python check_6g_now.py
    pause
    goto MENU
)
if "%CH%"=="7" (
    python restore_2pb.py
    pause
    goto MENU
)
if "%CH%"=="8" (
    del /q "telecom_sim_output\.admin_auth" 2>nul
    del /q "telecom_sim_output\.admin_salt" 2>nul
    echo [OK] Admin password reset. Restart the Admin app.
    pause
    goto MENU
)
if "%CH%"=="0" exit /b 0

goto MENU
