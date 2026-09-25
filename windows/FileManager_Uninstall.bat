@echo off
:: ══════════════════════════════════════════════════════════════
:: File Manager — Windows Uninstaller
:: ══════════════════════════════════════════════════════════════

title File Manager Uninstaller
cls
echo.
echo   +--------------------------------------------+
echo   ^|     File Manager -- Uninstaller            ^|
echo   ^|            Windows Version                 ^|
echo   +--------------------------------------------+
echo.
echo   This will remove File Manager from your PC.
echo.
echo   The following will be deleted:
echo     %USERPROFILE%\Desktop\FileSorter\
echo     %USERPROFILE%\Desktop\FileManager.bat
echo.
echo   Your sorted files and folders are NOT affected.
echo   Only the app itself will be removed.
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

:: Stop any running server
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

set REMOVED=0

:: Remove FileSorter folder
if exist "%USERPROFILE%\Desktop\FileSorter" (
    rmdir /s /q "%USERPROFILE%\Desktop\FileSorter"
    echo   Removed : %USERPROFILE%\Desktop\FileSorter\
    set /a REMOVED+=1
) else (
    echo   Skipped : FileSorter\ not found
)

:: Remove Windows launcher
if exist "%USERPROFILE%\Desktop\FileManager.bat" (
    del /f /q "%USERPROFILE%\Desktop\FileManager.bat"
    echo   Removed : %USERPROFILE%\Desktop\FileManager.bat
    set /a REMOVED+=1
) else (
    echo   Skipped : FileManager.bat not found
)

:: Remove Setup file from Desktop if it was copied there
if exist "%USERPROFILE%\Desktop\FileManager_Setup.bat" (
    del /f /q "%USERPROFILE%\Desktop\FileManager_Setup.bat"
    echo   Removed : %USERPROFILE%\Desktop\FileManager_Setup.bat
    set /a REMOVED+=1
)

echo.
echo   +--------------------------------------------+
echo   ^|        Uninstall Complete!                 ^|
echo   +--------------------------------------------+
echo.
echo   File Manager has been fully removed from your PC.
echo   Your files and folders are untouched.
echo.
echo   To reinstall in the future:
echo   Run FileManager_Setup.bat again.
echo.
pause
exit /b 0
