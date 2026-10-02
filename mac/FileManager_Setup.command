#!/bin/bash
# ══════════════════════════════════════════════════════════════
# File Manager — Mac Installer
# Double-click this file to install everything automatically.
# ══════════════════════════════════════════════════════════════

clear
echo ""
echo "  +----------------------------------------------+"
echo "  |        File Manager — Installer              |"
echo "  |              macOS Version                   |"
echo "  +----------------------------------------------+"
echo ""
echo "  This will install File Manager on your Mac."
echo "  Everything will be set up automatically."
echo ""
echo "  Press Enter to start, or close this window to cancel."
read

# ── Paths ──────────────────────────────────────────────────────
DEST="$HOME/Desktop/FileSorter"
LAUNCHER="$HOME/Desktop/FileManager.command"

# ── Step 1: Find Python ────────────────────────────────────────
echo ""
echo "  [1/6] Looking for Python 3..."
echo ""

PYTHON=""
for P in \
    /usr/local/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if [ -x "$P" ]; then
        PYTHON="$P"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    PYTHON=$(command -v python3 2>/dev/null)
fi

if [ -z "$PYTHON" ]; then
    echo ""
    echo "  ERROR: Python 3 not found on this Mac."
    echo ""
    echo "  Please install Python 3:"
    echo "  1. Your browser will open python.org"
    echo "  2. Download the macOS installer"
    echo "  3. Install it"
    echo "  4. Double-click FileManager_Setup.command again"
    echo ""
    open "https://www.python.org/downloads/"
    echo "  Press Enter to close."
    read
    exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1)
echo "  OK  Found: $PY_VER"

# ── Step 2: Install Pillow ─────────────────────────────────────
echo ""
echo "  [2/6] Installing Pillow (image compression)..."
echo ""

"$PYTHON" -m pip install Pillow --quiet --upgrade 2>/dev/null
if "$PYTHON" -c "from PIL import Image" 2>/dev/null; then
    echo "  OK  Pillow installed"
else
    echo "  WARN Pillow failed - compression will be skipped"
fi

# ── Step 3: Install PyWebView ──────────────────────────────────
echo ""
echo "  [3/6] Installing PyWebView (desktop window)..."
echo ""

"$PYTHON" -m pip install pywebview --quiet --upgrade 2>/dev/null
if "$PYTHON" -c "import webview" 2>/dev/null; then
    echo "  OK  PyWebView installed"
else
    echo "  WARN PyWebView failed - will use browser fallback"
fi

# ── Step 4: Create folder ──────────────────────────────────────
echo ""
echo "  [4/6] Setting up FileSorter folder..."
echo ""

mkdir -p "$DEST"
echo "  OK  Created: $DEST"

# ── Step 5: Copy scripts ───────────────────────────────────────
echo ""
echo "  [5/6] Installing scripts..."
echo ""

# Get repo root (parent of mac/ folder)
REPO_ROOT="$(dirname "$0")/.."
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

# file_manager.py
if [ -f "$REPO_ROOT/file_manager.py" ]; then
    cp "$REPO_ROOT/file_manager.py" "$DEST/file_manager.py"
    echo "  OK  file_manager.py copied"
else
    echo "  Downloading file_manager.py..."
    curl -s -L -o "$DEST/file_manager.py" \
        "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager.py"
    if [ -f "$DEST/file_manager.py" ]; then
        echo "  OK  file_manager.py downloaded"
    else
        echo "  ERROR: Could not get file_manager.py"
        echo "  Check your internet connection and try again."
        read; exit 1
    fi
fi

# file_manager_ui.py
if [ -f "$REPO_ROOT/file_manager_ui.py" ]; then
    cp "$REPO_ROOT/file_manager_ui.py" "$DEST/file_manager_ui.py"
    echo "  OK  file_manager_ui.py copied"
else
    echo "  Downloading file_manager_ui.py..."
    curl -s -L -o "$DEST/file_manager_ui.py" \
        "https://raw.githubusercontent.com/shahirzambri/file-manager/main/file_manager_ui.py"
    if [ -f "$DEST/file_manager_ui.py" ]; then
        echo "  OK  file_manager_ui.py downloaded"
    else
        echo "  ERROR: Could not get file_manager_ui.py"
        echo "  Check your internet connection and try again."
        read; exit 1
    fi
fi

# ── Step 6: Create launcher ────────────────────────────────────
echo ""
echo "  [6/6] Creating launcher on Desktop..."
echo ""

cat > "$LAUNCHER" << 'LAUNCHEOF'
#!/bin/bash
echo ""
echo "  Starting File Manager..."
echo ""

pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 1

python3 ~/Desktop/FileSorter/file_manager_ui.py
LAUNCHEOF

chmod +x "$LAUNCHER"
echo "  OK  FileManager.command created on Desktop"

# ── Done ───────────────────────────────────────────────────────
echo ""
echo "  +----------------------------------------------+"
echo "  |        Installation Complete!               |"
echo "  +----------------------------------------------+"
echo ""
echo "  Files installed:"
echo "    ~/Desktop/FileSorter/file_manager.py"
echo "    ~/Desktop/FileSorter/file_manager_ui.py"
echo "    ~/Desktop/FileManager.command"
echo ""
echo "  How to launch File Manager:"
echo "  Double-click FileManager.command on your Desktop"
echo ""
echo "  Tip: Drag FileManager.command to your Dock"
echo "  for quick access anytime!"
echo ""
read -p "  Launch File Manager now? (Y/n): " LAUNCH
if [[ "$LAUNCH" != "n" && "$LAUNCH" != "N" ]]; then
    echo ""
    echo "  Launching..."
    open "$LAUNCHER"
fi

echo ""
echo "  Press Enter to close this window."
read
