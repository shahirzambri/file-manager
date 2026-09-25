@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Installer
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
        goto :EXIT
    )
)
goto :FRESH

:REINSTALL
echo   Removing old installation...
rmdir /s /q "%USERPROFILE%\Desktop\FileSorter" 2>nul
del /f /q "%USERPROFILE%\Desktop\FileManager.bat" 2>nul
echo   Done.
echo.

:FRESH
echo   Welcome! This will set up File Manager on your PC.
echo.
echo   Press Enter to start, or close this window to cancel.
pause >nul

:: ══════════════════════════════════════════════════════════════
:: STEP 1 — FIND WORKING PYTHON
:: Uses a real test (python -c "print") not just --version
:: This avoids the Windows Store stub false positive
:: ══════════════════════════════════════════════════════════════
echo.
echo   [1/6] Checking Python...
echo.

set PYTHON_CMD=

:: Test if "python" actually works (not just the Store stub)
python -c "import sys; print(sys.version)" >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2^>nul') do set PY_VER_NUM=%%i
    echo   OK  Python is working
    goto :PYTHON_READY
)

:: Test "py" launcher (alternative on Windows)
py -c "import sys; print(sys.version)" >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=py
    echo   OK  Python is working (via py launcher)
    goto :PYTHON_READY
)

:: Test common install paths directly
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" -c "print('ok')" >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
        echo   OK  Python found at Python312
        goto :PYTHON_READY
    )
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" -c "print('ok')" >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
        echo   OK  Python found at Python311
        goto :PYTHON_READY
    )
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" -c "print('ok')" >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
        echo   OK  Python found at Python310
        goto :PYTHON_READY
    )
)

:: Python not working — download and install
echo   Python not found or not working.
echo   Downloading and installing Python 3.12 automatically...
echo.

curl --version >nul 2>&1
if %errorlevel% == 0 (
    echo   Downloading... please wait...
    curl -L --progress-bar -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
) else (
    echo   Downloading via PowerShell... please wait...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
)

if not exist "%TEMP%\python_installer.exe" (
    echo.
    echo   ERROR: Could not download Python.
    echo.
    echo   Please install manually:
    echo   1. Go to https://python.org/downloads
    echo   2. Click Download Python
    echo   3. Run the installer
    echo   4. TICK "Add Python to PATH"
    echo   5. Run this installer again
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo   Download complete. Installing Python silently...
"%TEMP%\python_installer.exe" /passive PrependPath=1 Include_pip=1 InstallAllUsers=0
del /f /q "%TEMP%\python_installer.exe" 2>nul

echo   Waiting for install to finish...
timeout /t 10 /nobreak >nul

:: Update PATH immediately
set "PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python312;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"

:: Test again after install
python -c "print('ok')" >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    echo   OK  Python installed successfully
    goto :PYTHON_READY
)

"%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" -c "print('ok')" >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD="%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    echo   OK  Python installed successfully
    goto :PYTHON_READY
)

echo.
echo   Python installed but PATH needs refreshing.
echo.
echo   Please:
echo   1. Close this window
echo   2. Open a NEW Command Prompt
echo   3. Run this installer again from the new window
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

:: Get repo root (parent of windows/ folder)
for %%F in ("%~dp0..") do set "REPO_ROOT=%%~fF"

:: ── file_manager.py ──────────────────────────────────────────
if exist "%REPO_ROOT%\file_manager.py" (
    copy /y "%REPO_ROOT%\file_manager.py" "%DEST%\file_manager.py" >nul
    echo   OK  file_manager.py copied from ZIP
) else (
    echo   Downloading file_manager.py from GitHub...
    curl -s -L -o "%DEST%\file_manager.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py" 2>nul
    if not exist "%DEST%\file_manager.py" (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py' -OutFile '%DEST%\file_manager.py'" 2>nul
    )
    if exist "%DEST%\file_manager.py" (
        echo   OK  file_manager.py downloaded
    ) else (
        echo   ERROR: Could not get file_manager.py
        echo   Check your internet and try again.
        pause
        exit /b 1
    )
)

:: ── file_manager_ui.py ───────────────────────────────────────
if exist "%REPO_ROOT%\file_manager_ui.py" (
    copy /y "%REPO_ROOT%\file_manager_ui.py" "%DEST%\file_manager_ui.py" >nul
    echo   OK  file_manager_ui.py copied from ZIP
) else (
    echo   Downloading file_manager_ui.py from GitHub...
    curl -s -L -o "%DEST%\file_manager_ui.py" "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py" 2>nul
    if not exist "%DEST%\file_manager_ui.py" (
        powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py' -OutFile '%DEST%\file_manager_ui.py'" 2>nul
    )
    if exist "%DEST%\file_manager_ui.py" (
        echo   OK  file_manager_ui.py downloaded
    ) else (
        echo   ERROR: Could not get file_manager_ui.py
        echo   Check your internet and try again.
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
    echo   WARN file_manager.py has issues - try reinstalling
)

%PYTHON_CMD% -m py_compile "%DEST%\file_manager_ui.py" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  file_manager_ui.py
) else (
    echo   WARN file_manager_ui.py has issues - try reinstalling
)

:: ══════════════════════════════════════════════════════════════
:: STEP 6 — CREATE LAUNCHER
:: Simple 3-line launcher - no pipe chars - no syntax errors
:: file_manager_ui.py handles port cleanup internally
:: ══════════════════════════════════════════════════════════════
echo.
echo   [6/6] Creating launcher on Desktop...
echo.

:: Write launcher using Python to avoid bat escaping issues
%PYTHON_CMD% -c "
import os
dest = os.path.join(os.path.expanduser('~'), 'Desktop', 'FileManager.bat')
py_cmd = r'%PYTHON_CMD%'.strip('\"')
script = os.path.join(os.path.expanduser('~'), 'Desktop', 'FileSorter', 'file_manager_ui.py')
lines = [
    '@echo off',
    'title File Manager',
    'echo.',
    'echo   Starting File Manager...',
    'echo.',
    'python \"' + script + '\"',
    'if errorlevel 1 py \"' + script + '\"',
    'if errorlevel 1 (',
    '    echo.',
    '    echo   ERROR: Could not start File Manager.',
    '    echo   Make sure Python is installed correctly.',
    '    pause',
    ')',
]
with open(dest, 'w') as f:
    f.write('\r\n'.join(lines))
print('  OK  FileManager.bat created on Desktop')
"

:: ══════════════════════════════════════════════════════════════
:: DONE
:: ══════════════════════════════════════════════════════════════
echo.
echo   +--------------------------------------------+
echo   ^|        Installation Complete!             ^|
echo   +--------------------------------------------+
echo.
echo   Everything is ready!
echo.
echo   TO LAUNCH FILE MANAGER ANYTIME:
echo   Double-click FileManager.bat on your Desktop
echo.
set /p LAUNCH="  Launch File Manager now? (Y/n): "
if /i "%LAUNCH%"=="n" goto :DONE
if /i "%LAUNCH%"=="no" goto :DONE
goto :LAUNCH

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
