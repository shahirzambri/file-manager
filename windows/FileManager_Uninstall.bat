@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Uninstaller
:: ══════════════════════════════════════════════════════════════

title File Manager Uninstaller
cls
echo.
echo   +--------------------------------------------+
echo   ^|     File Manager -- Uninstaller            ^|
echo   +--------------------------------------------+
echo.
echo   This will remove File Manager from your PC.
echo.
echo   The following will be deleted:
echo     %USERPROFILE%\Desktop\FileSorter\
echo     %USERPROFILE%\Desktop\FileManager.bat
echo.
echo   Your sorted files and folders are NOT affected.
echo.
set /p CONFIRM="  Are you sure? (y/N): "
echo.

if /i "%CONFIRM%"=="y" goto :UNINSTALL
if /i "%CONFIRM%"=="yes" goto :UNINSTALL

echo   Cancelled. Nothing was removed.
echo.
pause
exit /b 0

:UNINSTALL
echo   Uninstalling...
echo.

:: Stop any running instance
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Remove FileSorter folder
if exist "%USERPROFILE%\Desktop\FileSorter" (
    rmdir /s /q "%USERPROFILE%\Desktop\FileSorter"
    echo   Removed : %USERPROFILE%\Desktop\FileSorter\
) else (
    echo   Skipped : FileSorter\ not found
)

:: Remove launcher
if exist "%USERPROFILE%\Desktop\FileManager.bat" (
    del /f /q "%USERPROFILE%\Desktop\FileManager.bat"
    echo   Removed : FileManager.bat
) else (
    echo   Skipped : FileManager.bat not found
)

:: Remove setup file from Desktop if copied there
if exist "%USERPROFILE%\Desktop\FileManager_Setup.bat" (
    del /f /q "%USERPROFILE%\Desktop\FileManager_Setup.bat"
    echo   Removed : FileManager_Setup.bat
)

echo.
echo   +--------------------------------------------+
echo   ^|        Uninstall Complete!                 ^|
echo   +--------------------------------------------+
echo.
echo   File Manager has been fully removed.
echo   Your files and folders are untouched.
echo.
echo   To reinstall: Run FileManager_Setup.bat again.
echo.
pause
exit /b 0
