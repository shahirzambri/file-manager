@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Installer
:: Self-contained — no other files needed
:: Double-click this to install everything
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

goto :INSTALL

:REINSTALL
echo   Removing old installation...
rmdir /s /q "%USERPROFILE%\Desktop\FileSorter" 2>nul
del "%USERPROFILE%\Desktop\FileManager.bat" 2>nul
echo   Done. Reinstalling...
echo.

:INSTALL
echo   Press Enter to start installation, or close this window to cancel.
pause >nul

:: ── Step 1: Check Python ──────────────────────────────────────
echo.
echo   [1/5] Checking Python 3...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python 3 not found!
    echo.
    echo   Please install Python 3:
    echo   1. Go to https://python.org/downloads
    echo   2. Download the Windows installer
    echo   3. Run it - TICK "Add Python to PATH"
    echo   4. Double-click this file again
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo   OK  Found: %PY_VER%

:: ── Step 2: Install Pillow ─────────────────────────────────────
echo.
echo   [2/5] Installing Pillow (image compression)...
echo.

python -m pip install Pillow --quiet --upgrade
python -c "from PIL import Image" >nul 2>&1
if %errorlevel% == 0 (
    echo   OK  Pillow installed - compression enabled
) else (
    echo   WARN Pillow failed - compression will be skipped
)

:: ── Step 3: Create folder ──────────────────────────────────────
echo.
echo   [3/5] Creating FileSorter folder...
echo.

if not exist "%USERPROFILE%\Desktop\FileSorter" (
    mkdir "%USERPROFILE%\Desktop\FileSorter"
)
echo   OK  %USERPROFILE%\Desktop\FileSorter

:: ── Step 4: Write scripts using Python ────────────────────────
echo.
echo   [4/5] Writing scripts...
echo.

:: Write file_manager.py using Python heredoc trick
python -c "
import sys, os
dest = os.path.join(os.path.expanduser('~'), 'Desktop', 'FileSorter')

# Try to copy from same folder as this bat file first
import pathlib
bat_dir = pathlib.Path(r'%~dp0').parent
fm_src = bat_dir / 'file_manager.py'
ui_src = bat_dir / 'file_manager_ui.py'

import shutil
copied = 0

if fm_src.exists():
    shutil.copy2(fm_src, os.path.join(dest, 'file_manager.py'))
    print('  OK  file_manager.py copied')
    copied += 1

if ui_src.exists():
    shutil.copy2(ui_src, os.path.join(dest, 'file_manager_ui.py'))
    print('  OK  file_manager_ui.py copied')
    copied += 1

if copied < 2:
    # Download from GitHub
    import urllib.request
    base = 'https://raw.githubusercontent.com/shahirzambri/file-manager/main/'
    for fname in ['file_manager.py', 'file_manager_ui.py']:
        dst = os.path.join(dest, fname)
        if not os.path.exists(dst):
            try:
                print(f'  Downloading {fname} from GitHub...')
                urllib.request.urlretrieve(base + fname, dst)
                print(f'  OK  {fname} downloaded')
            except Exception as e:
                print(f'  WARN Could not get {fname}: {e}')
"

:: ── Step 5: Create launcher ────────────────────────────────────
echo.
echo   [5/5] Creating launcher on Desktop...
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
) > "%USERPROFILE%\Desktop\FileManager.bat"

echo   OK  FileManager.bat created on Desktop

:: ── Done ───────────────────────────────────────────────────────
echo.
echo   +--------------------------------------------+
echo   ^|        Installation Complete!             ^|
echo   +--------------------------------------------+
echo.
echo   Files created:
echo     %USERPROFILE%\Desktop\FileSorter\file_manager.py
echo     %USERPROFILE%\Desktop\FileSorter\file_manager_ui.py
echo     %USERPROFILE%\Desktop\FileManager.bat
echo.
echo   To launch File Manager anytime:
echo   Double-click FileManager.bat on your Desktop
echo.
set /p LAUNCH="  Launch File Manager now? (Y/n): "
if /i "%LAUNCH%"=="n" goto :DONE
if /i "%LAUNCH%"=="no" goto :DONE

:LAUNCH
echo.
echo   Launching...
start "" "%USERPROFILE%\Desktop\FileManager.bat"
goto :DONE

:EXIT
echo   Cancelled.

:DONE
echo.
pause
exit /b 0
