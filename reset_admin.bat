@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Reset Admin Password
REM  Deletes auth files. Next launch shows "First-time setup".
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul

set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || (
    echo [X] Cannot cd to %PROJ%
    pause
    exit /b 1
)

set "AUTH=telecom_sim_output\.admin_auth"
set "SALT=telecom_sim_output\.admin_salt"

echo ============================================================
echo   TELECOM-NET-SIM  ^|  Reset Admin Password
echo ============================================================
echo.
echo   This will delete:
echo     - %AUTH%
echo     - %SALT%
echo.
echo   The Admin Panel will then ask you to set a NEW password
echo   on its next launch.
echo.

REM ---------- Show current status ----------
if exist "%AUTH%" (
    echo   [i] Current auth file:  PRESENT
    for %%F in ("%AUTH%") do echo       Size: %%~zF bytes  Modified: %%~tF
) else (
    echo   [i] Current auth file:  not found
)

if exist "%SALT%" (
    echo   [i] Current salt file:  PRESENT
    for %%F in ("%SALT%") do echo       Size: %%~zF bytes  Modified: %%~tF
) else (
    echo   [i] Current salt file:  not found
)

echo.

if not exist "%AUTH%" if not exist "%SALT%" (
    echo   [!] Nothing to reset. Admin password is not set.
    echo.
    pause
    exit /b 0
)

REM ---------- Confirm ----------
set /p "CH=Type YES to confirm reset: "
if /i not "%CH%"=="YES" (
    echo.
    echo [i] Cancelled. No changes made.
    pause
    exit /b 0
)

REM ---------- Backup before deleting ----------
set "BACKUP_DIR=_admin_auth_backup"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "tokens=2-4 delims=/ " %%A in ('date /t') do set "D=%%C%%A%%B"
for /f "tokens=1-2 delims=: " %%A in ('time /t') do set "T=%%A%%B"
set "T=%T: =0%"
set "STAMP=%D%_%T%"

if exist "%AUTH%" (
    copy /y "%AUTH%" "%BACKUP_DIR%\.admin_auth.%STAMP%.bak" >nul
    echo   [v] Backed up .admin_auth
)
if exist "%SALT%" (
    copy /y "%SALT%" "%BACKUP_DIR%\.admin_salt.%STAMP%.bak" >nul
    echo   [v] Backed up .admin_salt
)

REM ---------- Delete auth files ----------
if exist "%AUTH%" del /q "%AUTH%"
if exist "%SALT%" del /q "%SALT%"

echo.
echo ============================================================
echo   RESET COMPLETE
echo ============================================================
echo   Next steps:
echo     1) Restart the Admin app:
echo        streamlit run telecom_admin.py --server.port 8503
echo     2) Choose a new password (min 8 chars)
echo.
echo   Backups of old auth stored in:
echo     %BACKUP_DIR%\
echo.
echo   To restore the previous password:
echo     copy "%BACKUP_DIR%\.admin_auth.%STAMP%.bak" "%AUTH%"
echo     copy "%BACKUP_DIR%\.admin_salt.%STAMP%.bak" "%SALT%"
echo ============================================================
echo.

pause
endlocal
