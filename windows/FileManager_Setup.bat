@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Installer
:: Self-contained — handles Python install automatically
:: ══════════════════════════════════════════════════════════════

title File Manager Installer
cls
echo.
echo   +--------------------------------------------+
echo   ^|     File Manager -- Windows Installer      ^|
echo   +--------------------------------------------+
echo.

:: ── Check if already installed ────────────────────────────────
if exist "%USERPROFILE%\Desktop\FileSorter\file_manager.py" (
    if exist "%USERPROFILE%\Desktop\FileSorter\file_manager_ui.py" (
        echo   File Manager is already installed!
        echo.
        echo   What would you like to do?
        echo.
        echo   [1] Launch File Manager
        echo   [2] Reinstall everything fresh
        echo   [3] Exit
        echo.
        set /p CHOICE="  Enter 1, 2 or 3: "
        echo.
        if "%CHOICE%"=="1" goto :LAUNCH
        if "%CHOICE%"=="2" goto :REINSTALL
        if "%CHOICE%"=="3" goto :EXIT
        goto :EXIT
    )
)
goto :FRESH

:REINSTALL
echo   Removing old installation...
rmdir /s /q "%USERPROFILE%\Desktop\FileSorter" 2>nul
del "%USERPROFILE%\Desktop\FileManager.bat" 2>nul
echo   Done. Reinstalling...
echo.

:FRESH
echo   Welcome! This installer will set up File Manager on your PC.
echo   Everything is automatic — just follow the steps.
echo.
echo   Press Enter to start, or close this window to cancel.
pause >nul

:: ══════════════════════════════════════════════════════════════
:: STEP 1 — CHECK AND INSTALL PYTHON
:: ══════════════════════════════════════════════════════════════
echo.
echo   [1/6] Checking Python...
echo.

:: Check if Python already exists
python --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo   OK  Python already installed: %PY_VER%
    goto :PYTHON_READY
)

:: Python not found — download and install it automatically
echo   Python not found. Installing automatically...
echo.
echo   Downloading Python installer from python.org...
echo   This may take 1-2 minutes depending on your internet speed.
echo.

:: Check if curl is available (Windows 10+)
curl --version >nul 2>&1
if %errorlevel% == 0 (
    :: Download Python using curl
    curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" --progress-bar
) else (
    :: Download using PowerShell as fallback
    echo   Using PowerShell to download...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'}"
)

if not exist "%TEMP%\python_installer.exe" (
    echo.
    echo   ERROR: Could not download Python.
    echo.
    echo   Please install manually:
    echo   1. Go to https://python.org/downloads
    echo   2. Download and run the installer
    echo   3. TICK "Add Python to PATH"
    echo   4. Run this file again
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo   Download complete. Installing Python now...
echo   A Python installer window will appear.
echo.
echo   IMPORTANT:
echo   +------------------------------------------+
echo   ^|  Tick "Add Python to PATH"               ^|
echo   ^|  Then click Install Now                  ^|
echo   +------------------------------------------+
echo.
echo   Press Enter when you are ready...
pause >nul

:: Run Python installer
"%TEMP%\python_installer.exe" /passive PrependPath=1 Include_pip=1

:: Wait for install to complete
echo.
echo   Waiting for Python installation to complete...
timeout /t 10 /nobreak >nul

:: Refresh environment to pick up new Python
call refreshenv 2>nul

:: Check again
python --version >nul 2>&1
if %errorlevel% neq 0 (
    :: Try py launcher
    py --version >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD=py
        goto :PYTHON_READY
    )
    echo.
    echo   Python installed but not detected yet.
    echo   Please CLOSE this window and run the installer again.
    echo.
    pause
    exit /b 1
)

:PYTHON_READY
:: Set python command
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=py
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PY_VER=%%i
echo   OK  Python ready: %PY_VER%

:: Clean up installer
del "%TEMP%\python_installer.exe" 2>nul

:: ══════════════════════════════════════════════════════════════
:: STEP 2 — INSTALL PILLOW
:: ══════════════════════════════════════════════════════════════
echo.
echo   [2/6] Installing Pillow (image compression)...
echo.

%PYTHON_CMD% -m pip install Pillow --quiet --upgrade
%PYTHON_CMD% -c "from PIL import Image" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  Pillow installed - compression enabled
) else (
    echo   WARN Pillow failed - compression will be skipped
    echo        You can try later: pip install Pillow
)

:: ══════════════════════════════════════════════════════════════
:: STEP 3 — CREATE FOLDER
:: ══════════════════════════════════════════════════════════════
echo.
echo   [3/6] Creating FileSorter folder...
echo.

if not exist "%USERPROFILE%\Desktop\FileSorter" (
    mkdir "%USERPROFILE%\Desktop\FileSorter"
)
echo   OK  %USERPROFILE%\Desktop\FileSorter

:: ══════════════════════════════════════════════════════════════
:: STEP 4 — COPY OR DOWNLOAD SCRIPTS
:: ══════════════════════════════════════════════════════════════
echo.
echo   [4/6] Getting scripts...
echo.

set "DEST=%USERPROFILE%\Desktop\FileSorter"
set "BAT_DIR=%~dp0"

:: Try to find scripts relative to this bat file
:: BAT is in windows/ so parent folder has the .py files
for %%F in ("%BAT_DIR%..") do set "REPO_ROOT=%%~fF"

:: Copy file_manager.py
if exist "%REPO_ROOT%\file_manager.py" (
    copy /y "%REPO_ROOT%\file_manager.py" "%DEST%\file_manager.py" >nul
    echo   OK  file_manager.py copied
) else (
    echo   Downloading file_manager.py from GitHub...
    curl -L -o "%DEST%\file_manager.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py" 2>nul
    if exist "%DEST%\file_manager.py" (
        echo   OK  file_manager.py downloaded
    ) else (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py' -OutFile '%DEST%\file_manager.py'"
        echo   OK  file_manager.py downloaded
    )
)

:: Copy file_manager_ui.py
if exist "%REPO_ROOT%\file_manager_ui.py" (
    copy /y "%REPO_ROOT%\file_manager_ui.py" "%DEST%\file_manager_ui.py" >nul
    echo   OK  file_manager_ui.py copied
) else (
    echo   Downloading file_manager_ui.py from GitHub...
    curl -L -o "%DEST%\file_manager_ui.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py" 2>nul
    if exist "%DEST%\file_manager_ui.py" (
        echo   OK  file_manager_ui.py downloaded
    ) else (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py' -OutFile '%DEST%\file_manager_ui.py'"
        echo   OK  file_manager_ui.py downloaded
    )
)

:: Verify scripts exist
if not exist "%DEST%\file_manager.py" (
    echo.
    echo   ERROR: Could not get file_manager.py
    echo   Check your internet connection and try again.
    pause
    exit /b 1
)

if not exist "%DEST%\file_manager_ui.py" (
    echo.
    echo   ERROR: Could not get file_manager_ui.py
    echo   Check your internet connection and try again.
    pause
    exit /b 1
)

:: ══════════════════════════════════════════════════════════════
:: STEP 5 — VERIFY SCRIPTS WORK
:: ══════════════════════════════════════════════════════════════
echo.
echo   [5/6] Verifying scripts...
echo.

%PYTHON_CMD% -m py_compile "%DEST%\file_manager.py" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  file_manager.py verified
) else (
    echo   WARN file_manager.py may have issues
)

%PYTHON_CMD% -m py_compile "%DEST%\file_manager_ui.py" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  file_manager_ui.py verified
) else (
    echo   WARN file_manager_ui.py may have issues
)

:: ══════════════════════════════════════════════════════════════
:: STEP 6 — CREATE LAUNCHER
:: ══════════════════════════════════════════════════════════════
echo.
echo   [6/6] Creating launcher on Desktop...
echo.

(
    echo @echo off
    echo title File Manager
    echo echo.
    echo echo   Starting File Manager...
    echo echo.
    echo.
    echo :: Kill old instance on port 8765
    echo for /f "tokens=5" %%%%a in ^('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"'^) do ^(
    echo     taskkill /F /PID %%%%a ^>nul 2^>^&1
    echo ^)
    echo timeout /t 2 /nobreak ^>nul
    echo.
    echo :: Start server - browser opens automatically
    echo python "%%USERPROFILE%%\Desktop\FileSorter\file_manager_ui.py"
    echo if %%errorlevel%% neq 0 ^(
    echo     py "%%USERPROFILE%%\Desktop\FileSorter\file_manager_ui.py"
    echo ^)
) > "%USERPROFILE%\Desktop\FileManager.bat"

echo   OK  FileManager.bat created on Desktop

:: ══════════════════════════════════════════════════════════════
:: DONE
:: ══════════════════════════════════════════════════════════════
echo.
echo   +--------------------------------------------+
echo   ^|        Installation Complete!             ^|
echo   +--------------------------------------------+
echo.
echo   Installed:
echo     - Python %PY_VER%
echo     - Pillow  (image compression)
echo     - File Manager scripts
echo     - FileManager.bat launcher on Desktop
echo.
echo   HOW TO USE:
echo   Double-click FileManager.bat on your Desktop
echo.
set /p LAUNCH="  Launch File Manager now? (Y/n): "
if /i "%LAUNCH%"=="n" goto :DONE
if /i "%LAUNCH%"=="no" goto :DONE

:LAUNCH
echo.
echo   Starting File Manager...
start "" "%USERPROFILE%\Desktop\FileManager.bat"
goto :DONE

:EXIT
echo   Exiting...

:DONE
echo.
pause
exit /b 0
