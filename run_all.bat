@echo off
REM ============================================================
REM  TELECOM-NET-SIM | Full Project Launcher
REM  Runs database checks, launches 3 Streamlit apps, opens browsers
REM ============================================================
setlocal EnableDelayedExpansion
chcp 65001 > nul

REM ---------- Project directory ----------
set "PROJ=D:\simulation\mci"
cd /d "%PROJ%" || (
    echo [X] Cannot cd to %PROJ%
    pause
    exit /b 1
)

REM ---------- Ports ----------
set "PORT_DASH=8501"
set "PORT_RADAR=8502"
set "PORT_ADMIN=8503"

echo ============================================================
echo   TELECOM-NET-SIM  ^|  Full Launcher
echo ============================================================
echo   Project : %PROJ%
echo   Ports   : dashboard=%PORT_DASH%  radar=%PORT_RADAR%  admin=%PORT_ADMIN%
echo ============================================================
echo.

REM ---------- Python check ----------
where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python not found in PATH. Aborting.
    pause
    exit /b 1
)

REM ---------- Streamlit check ----------
python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo [!] Streamlit not installed. Installing...
    python -m pip install streamlit plotly pandas numpy kaleido
)

REM ---------- Database check ----------
if not exist "telecom_sim_output\telecom_sim.db" (
    echo [!] Database not found. Running simulator...
    python telecom_net_sim.py
    if errorlevel 1 ( echo [X] Simulator failed. & pause & exit /b 1 )
    python telecom_attack.py
    if errorlevel 1 ( echo [X] Attack generator failed. & pause & exit /b 1 )
    python restore_2pb.py
    if errorlevel 1 ( echo [!] restore_2pb skipped or failed )
) else (
    echo [i] Database found.
)

REM ---------- Quick 6G verification ----------
python check_6g_now.py
if errorlevel 1 ( echo [!] 6G check had issues, continuing anyway )
echo.

REM ---------- Kill existing Streamlit on these ports ----------
for %%P in (%PORT_DASH% %PORT_RADAR% %PORT_ADMIN%) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
        echo [i] Killing PID %%A on port %%P
        taskkill /F /PID %%A >nul 2>nul
    )
)

REM ---------- Launch three Streamlit apps in separate windows ----------
echo.
echo [1/3] Launching Dashboard on port %PORT_DASH% ...
start "TELECOM Dashboard" cmd /k "cd /d %PROJ% && python -m streamlit run telecom_dashboard.py --server.port %PORT_DASH% --server.headless true"

timeout /t 2 /nobreak >nul

echo [2/3] Launching Radar on port %PORT_RADAR% ...
start "TELECOM Radar" cmd /k "cd /d %PROJ% && python -m streamlit run telecom_radar.py --server.port %PORT_RADAR% --server.headless true"

timeout /t 2 /nobreak >nul

echo [3/3] Launching Admin on port %PORT_ADMIN% ...
start "TELECOM Admin" cmd /k "cd /d %PROJ% && python -m streamlit run telecom_admin.py --server.port %PORT_ADMIN% --server.headless true"

REM ---------- Wait for Streamlit to boot ----------
echo.
echo [i] Waiting 8 seconds for Streamlit apps to start ...
timeout /t 8 /nobreak >nul

REM ---------- Open browsers ----------
start "" "http://localhost:%PORT_DASH%"
start "" "http://localhost:%PORT_RADAR%"
start "" "http://localhost:%PORT_ADMIN%"

echo.
echo ============================================================
echo   ALL APPS LAUNCHED
echo ============================================================
echo   Dashboard : http://localhost:%PORT_DASH%
echo   Radar     : http://localhost:%PORT_RADAR%
echo   Admin     : http://localhost:%PORT_ADMIN%
echo.
echo   To stop an app  : close its window OR press Ctrl+C inside it
echo   To stop all     : run stop_all.bat
echo ============================================================
echo.
pause
endlocal