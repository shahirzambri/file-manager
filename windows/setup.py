#!/usr/bin/env python3
"""
File Manager — Windows Setup Script
Run this once to install everything.
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

DEST    = Path.home() / "Desktop" / "FileSorter"
DESKTOP = Path.home() / "Desktop"

# ── Files to download from GitHub ────────────────────────────────
GITHUB_RAW = "https://raw.githubusercontent.com/shahirzambri/file-manager/main/"

FILES = {
    "file_manager.py"    : GITHUB_RAW + "file_manager.py",
    "file_manager_ui.py" : GITHUB_RAW + "file_manager_ui.py",
}

# ── Launcher content ──────────────────────────────────────────────
LAUNCHER = r"""@echo off
title File Manager
echo.
echo   Starting File Manager...
echo.

:: Kill any old instance on port 8765
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start server
:: Browser opens automatically from inside file_manager_ui.py
:: Do NOT open browser here — would cause double tab
python "%USERPROFILE%\Desktop\FileSorter\file_manager_ui.py"
"""

:: Wait for server to respond
echo Waiting for server...
set COUNT=0
:LOOP
set /a COUNT+=1
if %COUNT% gtr 20 goto FAIL
timeout /t 1 /nobreak >nul
curl -s http://localhost:8765 >nul 2>&1
if %ERRORLEVEL% == 0 goto READY
echo Attempt %COUNT% of 20...
goto LOOP

:READY
echo Server ready!
start http://localhost:8765
echo Browser opened. Minimize this window.
pause
exit /b 0

:FAIL
echo Server did not start. Please try again.
pause
exit /b 1
"""


def step(n, total, msg):
    print(f"\n  [{n}/{total}] {msg}...")


def ok(msg):
    print(f"  OK   {msg}")


def warn(msg):
    print(f"  WARN {msg}")


def fail(msg):
    print(f"\n  ERROR: {msg}\n")
    input("  Press Enter to close.")
    sys.exit(1)


def main():
    print()
    print("  +------------------------------------------+")
    print("  |   File Manager -- Windows Installer      |")
    print("  +------------------------------------------+")
    print()
    print("  This will install File Manager on your PC.")
    print()
    input("  Press Enter to start, or close this window to cancel.")

    # ── Step 1: Check Python ──────────────────────────────────────
    step(1, 5, "Checking Python 3")
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 9):
        fail(f"Python 3.9+ required. You have {sys.version}\n"
             "  Download from: https://python.org/downloads\n"
             "  IMPORTANT: tick 'Add Python to PATH' during install")
    ok(f"Found Python {ver.major}.{ver.minor}.{ver.micro}")

    # ── Step 2: Install Pillow ────────────────────────────────────
    step(2, 5, "Installing Pillow (image compression)")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "Pillow",
             "--quiet", "--upgrade"],
            check=True
        )
        ok("Pillow installed — image compression enabled")
    except Exception:
        warn("Pillow could not be installed — compression will be skipped")

    # ── Step 3: Create folder ─────────────────────────────────────
    step(3, 5, "Creating FileSorter folder")
    DEST.mkdir(parents=True, exist_ok=True)
    ok(f"Created: {DEST}")

    # ── Step 4: Download scripts ──────────────────────────────────
    step(4, 5, "Downloading scripts from GitHub")

    for filename, url in FILES.items():
        target = DEST / filename
        try:
            print(f"  Downloading {filename}...")
            urllib.request.urlretrieve(url, target)
            ok(f"{filename} downloaded")
        except Exception as e:
            # If download fails — copy from same folder as this script
            local = Path(__file__).parent.parent / filename
            if local.exists():
                import shutil
                shutil.copy(local, target)
                ok(f"{filename} copied from local files")
            else:
                warn(f"Could not get {filename}: {e}")

    # ── Step 5: Create launcher ───────────────────────────────────
    step(5, 5, "Creating launcher on Desktop")
    launcher_path = DESKTOP / "FileManager.bat"
    launcher_path.write_text(LAUNCHER)
    ok(f"FileManager.bat created on Desktop")

    # ── Done ──────────────────────────────────────────────────────
    print()
    print("  +------------------------------------------+")
    print("  |        Installation Complete!            |")
    print("  +------------------------------------------+")
    print()
    print("  Files installed:")
    print(f"    {DEST / 'file_manager.py'}")
    print(f"    {DEST / 'file_manager_ui.py'}")
    print(f"    {DESKTOP / 'FileManager.bat'}")
    print()
    print("  To launch File Manager anytime:")
    print("  Double-click FileManager.bat on your Desktop")
    print()

    launch = input("  Launch File Manager now? (Y/n): ").strip().lower()
    if launch not in ("n", "no"):
        launcher_path = DESKTOP / "FileManager.bat"
        if launcher_path.exists():
            os.startfile(str(launcher_path))

    input("  Press Enter to close this window.")


if __name__ == "__main__":
    main()
