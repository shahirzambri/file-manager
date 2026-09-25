#!/bin/bash
# ──────────────────────────────────────────────
# File Manager Launcher — macOS
# Opens as a desktop window via PyWebView
# ──────────────────────────────────────────────

echo ""
echo "  Starting File Manager..."
echo ""

# Kill any old instance
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 1

# Launch desktop app
python3 ~/Desktop/FileSorter/file_manager_ui.py
