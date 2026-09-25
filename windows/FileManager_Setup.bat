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
del /f /q "%USERPROFILE%\Desktop\FileManager.bat" 2>nul
echo   Done. Reinstalling...
echo.

:FRESH
echo   Welcome! This will set up File Manager on your PC.
echo   Everything is handled automatically.
echo.
echo   Press Enter to start, or close this window to cancel.
pause >nul

:: ══════════════════════════════════════════════════════════════
:: STEP 1 — CHECK AND INSTALL PYTHON
:: ══════════════════════════════════════════════════════════════
echo.
echo   [1/6] Checking Python...
echo.

python --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo   OK  Python already installed: %PY_VER%
    set PYTHON_CMD=python
    goto :PYTHON_READY
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    for /f "tokens=*" %%i in ('py --version 2^>^&1') do set PY_VER=%%i
    echo   OK  Python already installed: %PY_VER%
    set PYTHON_CMD=py
    goto :PYTHON_READY
)

:: Python not found — download and install automatically
echo   Python not found. Downloading and installing...
echo.
echo   This may take a few minutes depending on your internet speed.
echo.

curl --version >nul 2>&1
if %errorlevel% == 0 (
    echo   Downloading Python 3.12...
    curl -L -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" --progress-bar
) else (
    echo   Downloading Python 3.12 via PowerShell...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
)

if not exist "%TEMP%\python_installer.exe" (
    echo.
    echo   ERROR: Could not download Python.
    echo   Please install manually from https://python.org/downloads
    echo   IMPORTANT: Tick "Add Python to PATH" during install.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo   Installing Python silently...
"%TEMP%\python_installer.exe" /passive PrependPath=1 Include_pip=1 InstallAllUsers=0
del /f /q "%TEMP%\python_installer.exe" 2>nul

echo   Waiting for installation to finish...
timeout /t 8 /nobreak >nul

:: Refresh PATH
set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts"

python --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
    echo   OK  Python installed: %PY_VER%
    goto :PYTHON_READY
)

py --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=py
    for /f "tokens=*" %%i in ('py --version 2^>^&1') do set PY_VER=%%i
    echo   OK  Python installed: %PY_VER%
    goto :PYTHON_READY
)

echo.
echo   Python installed but needs a restart to activate.
echo   Please CLOSE this window, restart your PC, then run this installer again.
echo.
pause
exit /b 1

:PYTHON_READY

:: ══════════════════════════════════════════════════════════════
:: STEP 2 — INSTALL PILLOW
:: ══════════════════════════════════════════════════════════════
echo.
echo   [2/6] Installing Pillow...
echo.

%PYTHON_CMD% -m pip install Pillow --quiet --upgrade
%PYTHON_CMD% -c "from PIL import Image" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  Pillow installed
) else (
    echo   WARN Pillow failed - compression will be skipped
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

:: Get the repo root folder (parent of windows/)
for %%F in ("%~dp0..") do set "REPO_ROOT=%%~fF"

:: ── file_manager.py ──────────────────────────────────────────
if exist "%REPO_ROOT%\file_manager.py" (
    copy /y "%REPO_ROOT%\file_manager.py" "%DEST%\file_manager.py" >nul
    echo   OK  file_manager.py copied
) else (
    echo   Downloading file_manager.py...
    curl -s -L -o "%DEST%\file_manager.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py" 2>nul
    if not exist "%DEST%\file_manager.py" (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py' -OutFile '%DEST%\file_manager.py'" 2>nul
    )
    if exist "%DEST%\file_manager.py" (
        echo   OK  file_manager.py downloaded
    ) else (
        echo   ERROR: Could not get file_manager.py
        echo   Check your internet connection and try again.
        pause
        exit /b 1
    )
)

:: ── file_manager_ui.py ───────────────────────────────────────
if exist "%REPO_ROOT%\file_manager_ui.py" (
    copy /y "%REPO_ROOT%\file_manager_ui.py" "%DEST%\file_manager_ui.py" >nul
    echo   OK  file_manager_ui.py copied
) else (
    echo   Downloading file_manager_ui.py...
    curl -s -L -o "%DEST%\file_manager_ui.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py" 2>nul
    if not exist "%DEST%\file_manager_ui.py" (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py' -OutFile '%DEST%\file_manager_ui.py'" 2>nul
    )
    if exist "%DEST%\file_manager_ui.py" (
        echo   OK  file_manager_ui.py downloaded
    ) else (
        echo   ERROR: Could not get file_manager_ui.py
        echo   Check your internet connection and try again.
        pause
        exit /b 1
    )
)

:: ══════════════════════════════════════════════════════════════
:: STEP 5 — VERIFY
:: ══════════════════════════════════════════════════════════════
echo.
echo   [5/6] Verifying scripts...
echo.

%PYTHON_CMD% -m py_compile "%DEST%\file_manager.py" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  file_manager.py
) else (
    echo   WARN file_manager.py may have issues
)

%PYTHON_CMD% -m py_compile "%DEST%\file_manager_ui.py" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  file_manager_ui.py
) else (
    echo   WARN file_manager_ui.py may have issues
)

:: ══════════════════════════════════════════════════════════════
:: STEP 6 — CREATE LAUNCHER
:: Simple launcher — no pipe characters — no syntax errors
:: file_manager_ui.py handles port cleanup internally
:: ══════════════════════════════════════════════════════════════
echo.
echo   [6/6] Creating launcher...
echo.

set "LAUNCHER=%USERPROFILE%\Desktop\FileManager.bat"

%PYTHON_CMD% -c "
launcher = r'''@echo off
title File Manager
echo.
echo   Starting File Manager...
echo.
python \"%USERPROFILE%\Desktop\FileSorter\file_manager_ui.py\"
if errorlevel 1 (
    py \"%USERPROFILE%\Desktop\FileSorter\file_manager_ui.py\"
)
'''

import os
dest = os.path.join(os.path.expanduser('~'), 'Desktop', 'FileManager.bat')
content = '@echo off\r\ntitle File Manager\r\necho.\r\necho   Starting File Manager...\r\necho.\r\npython \"%%USERPROFILE%%\\Desktop\\FileSorter\\file_manager_ui.py\"\r\nif errorlevel 1 (\r\n    py \"%%USERPROFILE%%\\Desktop\\FileSorter\\file_manager_ui.py\"\r\n)\r\n'
with open(dest, 'w') as f:
    f.write(content)
print('  OK  FileManager.bat created')
"

:: ══════════════════════════════════════════════════════════════
:: DONE
:: ══════════════════════════════════════════════════════════════
echo.
echo   +--------------------------------------------+
echo   ^|        Installation Complete!             ^|
echo   +--------------------------------------------+
echo.
echo   Installed:
echo     - %PY_VER%
echo     - Pillow image library
echo     - File Manager scripts on Desktop
echo     - FileManager.bat launcher on Desktop
echo.
echo   TO USE FILE MANAGER ANYTIME:
echo   Double-click FileManager.bat on your Desktop
echo.
set /p LAUNCH="  Launch File Manager now? (Y/n): "
if /i "%LAUNCH%"=="n" goto :DONE
if /i "%LAUNCH%"=="no" goto :DONE

:LAUNCH
echo.
echo   Launching File Manager...
start "" "%USERPROFILE%\Desktop\FileManager.bat"
goto :DONE

:EXIT
echo   Exiting...
goto :DONE

:DONE
echo.
pause
exit /b 0
