#!/bin/bash
# ──────────────────────────────────────────────
# File Manager Launcher — macOS
# Browser opens automatically from the Python
# script itself. Do NOT open browser here.
# ──────────────────────────────────────────────

echo ""
echo "  Starting File Manager..."
echo ""

# Kill any old instance running on port 8765
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 1

# Start the server
# Browser opens automatically inside file_manager_ui.py
python3 ~/Desktop/FileSorter/file_manager_ui.py
