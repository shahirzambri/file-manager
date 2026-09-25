#!/bin/bash
# ══════════════════════════════════════════════════════════════
# File Manager — Mac Uninstaller
# ══════════════════════════════════════════════════════════════

clear
echo ""
echo "  +--------------------------------------------+"
echo "  |     File Manager -- Uninstaller            |"
echo "  |              macOS Version                 |"
echo "  +--------------------------------------------+"
echo ""
echo "  This will remove File Manager from your Mac."
echo ""
echo "  The following will be deleted:"
echo "    ~/Desktop/FileSorter/"
echo "    ~/Desktop/FileManager.command"
echo "    ~/Desktop/FileManager.app"
echo ""
echo "  Your sorted files and folders are NOT affected."
echo "  Only the app itself will be removed."
echo ""
read -p "  Are you sure? (y/N): " CONFIRM
echo ""

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "  Cancelled. Nothing was removed."
    echo ""
    exit 0
fi

echo "  Uninstalling..."
echo ""

# Stop any running server
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null

REMOVED=0

# Remove FileSorter folder
if [ -d "$HOME/Desktop/FileSorter" ]; then
    rm -rf "$HOME/Desktop/FileSorter"
    echo "  Removed : ~/Desktop/FileSorter/"
    REMOVED=$((REMOVED + 1))
else
    echo "  Skipped : ~/Desktop/FileSorter/ (not found)"
fi

# Remove Mac launcher
if [ -f "$HOME/Desktop/FileManager.command" ]; then
    rm -f "$HOME/Desktop/FileManager.command"
    echo "  Removed : ~/Desktop/FileManager.command"
    REMOVED=$((REMOVED + 1))
else
    echo "  Skipped : ~/Desktop/FileManager.command (not found)"
fi

# Remove Mac app
if [ -d "$HOME/Desktop/FileManager.app" ]; then
    rm -rf "$HOME/Desktop/FileManager.app"
    echo "  Removed : ~/Desktop/FileManager.app"
    REMOVED=$((REMOVED + 1))
else
    echo "  Skipped : ~/Desktop/FileManager.app (not found)"
fi

# Remove setup file
if [ -f "$HOME/Desktop/FileManager_Setup.command" ]; then
    rm -f "$HOME/Desktop/FileManager_Setup.command"
    echo "  Removed : ~/Desktop/FileManager_Setup.command"
    REMOVED=$((REMOVED + 1))
fi

echo ""
echo "  +--------------------------------------------+"
echo "  |        Uninstall Complete!                 |"
echo "  +--------------------------------------------+"
echo ""
echo "  $REMOVED item(s) removed."
echo ""
echo "  File Manager has been fully removed from your Mac."
echo "  Your files and folders are untouched."
echo ""
echo "  To reinstall in the future:"
echo "  Run FileManager_Setup.command again."
echo ""
