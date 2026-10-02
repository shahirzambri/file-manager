@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Installer
:: Opens as desktop window via PyWebView
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
        echo   [1] Launch File Manager
        echo   [2] Reinstall fresh
        echo   [3] Exit
        echo.
        set /p CHOICE="  Enter 1, 2 or 3: "
        echo.
        if "%CHOICE%"=="1" goto :LAUNCH
        if "%CHOICE%"=="2" goto :REINSTALL
        goto :EXIT
    )
)

echo   Welcome! This will set up File Manager on your PC.
echo.
echo   Press Enter to start, or close this window to cancel.
pause >nul
goto :INSTALL

:REINSTALL
echo   Removing old installation...
rmdir /s /q "%USERPROFILE%\Desktop\FileSorter" 2>nul
del /f /q "%USERPROFILE%\Desktop\FileManager.bat" 2>nul
echo   Done.
echo.

:INSTALL

:: ══════════════════════════════════════════════════════════════
:: STEP 1 — FIND PYTHON
:: ══════════════════════════════════════════════════════════════
echo.
echo   [1/7] Checking Python...
echo.

set PYTHON_CMD=

python -c "print('ok')" >nul 2>&1
if %errorlevel% == 0 set PYTHON_CMD=python

if "%PYTHON_CMD%"=="" (
    py -c "print('ok')" >nul 2>&1
    if %errorlevel% == 0 set PYTHON_CMD=py
)

if "%PYTHON_CMD%"=="" (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
        "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" -c "print('ok')" >nul 2>&1
        if %errorlevel% == 0 set "PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    )
)

if "%PYTHON_CMD%"=="" (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
        "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" -c "print('ok')" >nul 2>&1
        if %errorlevel% == 0 set "PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
    )
)

if "%PYTHON_CMD%"=="" goto :INSTALL_PYTHON

echo   OK  Python is working
goto :STEP2

:INSTALL_PYTHON
echo   Python not found. Downloading Python 3.12...
echo.

curl --version >nul 2>&1
if %errorlevel% == 0 (
    curl -L --progress-bar -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
) else (
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
)

if not exist "%TEMP%\python_installer.exe" (
    echo   ERROR: Could not download Python.
    echo   Please install from https://python.org/downloads
    echo   IMPORTANT: Tick "Add Python to PATH"
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Installing Python silently...
"%TEMP%\python_installer.exe" /passive PrependPath=1 Include_pip=1 InstallAllUsers=0
del /f /q "%TEMP%\python_installer.exe" 2>nul
timeout /t 10 /nobreak >nul

set "PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python312;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts;%PATH%"

python -c "print('ok')" >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_CMD=python
    echo   OK  Python installed
    goto :STEP2
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
    echo   OK  Python installed
    goto :STEP2
)

echo   Please close this window and run the installer again.
pause
exit /b 1

:: ══════════════════════════════════════════════════════════════
:: STEP 2 — PILLOW
:: ══════════════════════════════════════════════════════════════
:STEP2
echo.
echo   [2/7] Installing Pillow...
echo.

%PYTHON_CMD% -m pip install Pillow --quiet --upgrade
%PYTHON_CMD% -c "from PIL import Image" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  Pillow installed
) else (
    echo   WARN Pillow failed - compression will be skipped
)

:: ══════════════════════════════════════════════════════════════
:: STEP 3 — PYWEBVIEW
:: ══════════════════════════════════════════════════════════════
:STEP3
echo.
echo   [3/7] Installing PyWebView (desktop window)...
echo.

%PYTHON_CMD% -m pip install pywebview --quiet --upgrade
%PYTHON_CMD% -c "import webview" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  PyWebView installed - app opens as desktop window
) else (
    echo   WARN PyWebView failed - will try alternative
    %PYTHON_CMD% -m pip install pywebview[winforms] --quiet --upgrade
    %PYTHON_CMD% -c "import webview" >nul 2>&1
    if %errorlevel% == 0 (
        echo   OK  PyWebView installed via winforms
    ) else (
        echo   WARN PyWebView could not be installed
        echo        App will open in browser instead
    )
)

:: ══════════════════════════════════════════════════════════════
:: STEP 4 — CREATE FOLDER
:: ══════════════════════════════════════════════════════════════
:STEP4
echo.
echo   [4/7] Creating FileSorter folder...
echo.

if not exist "%USERPROFILE%\Desktop\FileSorter" mkdir "%USERPROFILE%\Desktop\FileSorter"
echo   OK  %USERPROFILE%\Desktop\FileSorter

:: ══════════════════════════════════════════════════════════════
:: STEP 5 — GET SCRIPTS
:: ══════════════════════════════════════════════════════════════
:STEP5
echo.
echo   [5/7] Getting scripts...
echo.

set "DEST=%USERPROFILE%\Desktop\FileSorter"
for %%F in ("%~dp0..") do set "REPO_ROOT=%%~fF"

:: file_manager.py
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
        pause
        exit /b 1
    )
)

:: file_manager_ui.py
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
        pause
        exit /b 1
    )
)

:: ══════════════════════════════════════════════════════════════
:: STEP 6 — VERIFY
:: ══════════════════════════════════════════════════════════════
:STEP6
echo.
echo   [6/7] Verifying...
echo.

%PYTHON_CMD% -m py_compile "%DEST%\file_manager.py" >nul 2>&1
if %errorlevel% == 0 (echo   OK  file_manager.py) else (echo   WARN file_manager.py has issues)

%PYTHON_CMD% -m py_compile "%DEST%\file_manager_ui.py" >nul 2>&1
if %errorlevel% == 0 (echo   OK  file_manager_ui.py) else (echo   WARN file_manager_ui.py has issues)

:: ══════════════════════════════════════════════════════════════
:: STEP 7 — CREATE LAUNCHER
:: Simple launcher — no pipe chars — no syntax errors
:: PyWebView opens desktop window automatically
:: ══════════════════════════════════════════════════════════════
:STEP7
echo.
echo   [7/7] Creating launcher...
echo.

set "LAUNCHER=%USERPROFILE%\Desktop\FileManager.bat"
set "SCRIPT=%USERPROFILE%\Desktop\FileSorter\file_manager_ui.py"

echo @echo off                                        > "%LAUNCHER%"
echo title File Manager                              >> "%LAUNCHER%"
echo echo.                                           >> "%LAUNCHER%"
echo echo   Starting File Manager...                 >> "%LAUNCHER%"
echo echo.                                           >> "%LAUNCHER%"
echo python "%SCRIPT%"                               >> "%LAUNCHER%"
echo if errorlevel 1 py "%SCRIPT%"                  >> "%LAUNCHER%"
echo if errorlevel 1 (                               >> "%LAUNCHER%"
echo     echo.                                       >> "%LAUNCHER%"
echo     echo   ERROR: Could not start.              >> "%LAUNCHER%"
echo     echo   Make sure Python is installed.       >> "%LAUNCHER%"
echo     pause                                       >> "%LAUNCHER%"
echo )                                               >> "%LAUNCHER%"

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
echo     - Python
echo     - Pillow (image compression)
echo     - PyWebView (desktop window)
echo     - File Manager scripts
echo     - FileManager.bat launcher on Desktop
echo.
echo   File Manager opens as a DESKTOP WINDOW
echo   No browser needed!
echo.
echo   TO LAUNCH ANYTIME:
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
