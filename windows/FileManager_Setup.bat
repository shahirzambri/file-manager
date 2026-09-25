@echo off
:: ══════════════════════════════════════════════════════
:: File Manager — Windows Installer
:: Double-click this to install File Manager on your PC
:: ══════════════════════════════════════════════════════

title File Manager Installer
cls
echo.
echo   File Manager -- Windows Installer
echo   ====================================
echo.

:: Check Python exists
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python not found!
    echo.
    echo   Please install Python 3 first:
    echo   1. Go to https://python.org/downloads
    echo   2. Download Windows installer
    echo   3. Run it and tick "Add Python to PATH"
    echo   4. Run this file again
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Run the Python setup script
echo   Python found. Running installer...
echo.
python "%~dp0setup.py"
