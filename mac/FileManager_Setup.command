#!/bin/bash
# ══════════════════════════════════════════════════════════════
# File Manager — Mac Installer
# Installs Pillow + PyWebView and creates FileManager.command
# No admin rights needed.
# ══════════════════════════════════════════════════════════════

clear
echo ""
echo "  +----------------------------------------------+"
echo "  |        File Manager — Installer              |"
echo "  |              macOS Version                   |"
echo "  +----------------------------------------------+"
echo ""
echo "  Press Enter to start, or close this window to cancel."
read

DEST="$HOME/Desktop/FileSorter"
LAUNCHER="$HOME/Desktop/FileManager.command"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="https://raw.githubusercontent.com/shahirzambri/file-manager/main"

# ── Helper: install a package, retry with --user if needed ────
install_pkg() {
    PKG="$1"; IMPORT="$2"
    "$PYTHON" -m pip install "$PKG" --quiet --upgrade 2>/dev/null
    if ! "$PYTHON" -c "import $IMPORT" 2>/dev/null; then
        "$PYTHON" -m pip install "$PKG" --quiet --upgrade --user 2>/dev/null
    fi
    "$PYTHON" -c "import $IMPORT" 2>/dev/null
}

# ── Step 1: Find Python ────────────────────────────────────────
echo ""
echo "  [1/6] Looking for Python 3..."

PYTHON=""
for P in \
    /usr/local/bin/python3 \
    /opt/homebrew/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3 \
    /usr/bin/python3; do
    if [ -x "$P" ] && "$P" -c "print('ok')" >/dev/null 2>&1; then
        PYTHON="$P"
        break
    fi
done
[ -z "$PYTHON" ] && PYTHON=$(command -v python3 2>/dev/null)

if [ -z "$PYTHON" ]; then
    echo "  ERROR: Python 3 not found."
    echo "  Install it from python.org, then run this installer again."
    open "https://www.python.org/downloads/"
    read; exit 1
fi
echo "  OK  $("$PYTHON" --version 2>&1)"

# ── Step 2: Upgrade pip ────────────────────────────────────────
echo ""
echo "  [2/6] Updating pip..."
"$PYTHON" -m pip install --upgrade pip --quiet 2>/dev/null \
  || "$PYTHON" -m pip install --upgrade pip --quiet --user 2>/dev/null
echo "  OK  pip ready"

# ── Step 3: Install Pillow ─────────────────────────────────────
echo ""
echo "  [3/6] Installing Pillow (image compression)..."
if install_pkg Pillow PIL; then
    echo "  OK  Pillow installed"
else
    echo "  WARN Pillow failed - compression will be skipped"
fi

# ── Step 4: Install PyWebView ──────────────────────────────────
echo ""
echo "  [4/6] Installing PyWebView (desktop window)..."
echo "        This can take a minute..."
if install_pkg pywebview webview; then
    echo "  OK  PyWebView installed"
else
    echo "  ERROR: PyWebView could not be installed."
    echo "  Try in Terminal:  xcode-select --install"
    echo "  Then run this installer again."
    read; exit 1
fi

# ── Step 5: Copy scripts ───────────────────────────────────────
echo ""
echo "  [5/6] Installing scripts..."
mkdir -p "$DEST"

for FNAME in file_manager.py file_manager_ui.py; do
    if [ "$REPO_ROOT" = "$DEST" ] && [ -f "$DEST/$FNAME" ]; then
        echo "  OK  $FNAME already in place"
    elif [ -f "$REPO_ROOT/$FNAME" ]; then
        cp "$REPO_ROOT/$FNAME" "$DEST/$FNAME"
        echo "  OK  $FNAME copied"
    else
        curl -s -L -o "$DEST/$FNAME" "$BASE_URL/$FNAME"
        if [ -s "$DEST/$FNAME" ]; then
            echo "  OK  $FNAME downloaded"
        else
            echo "  ERROR: Could not get $FNAME. Check your internet."
            read; exit 1
        fi
    fi
done

# ── Step 6: Create launcher ────────────────────────────────────
echo ""
echo "  [6/6] Creating launcher on Desktop..."

cat > "$LAUNCHER" << LAUNCHEOF
#!/bin/bash
echo ""
echo "  Starting File Manager..."
echo ""
pkill -9 -f file_manager_ui.py 2>/dev/null
lsof -ti:8765 | xargs kill -9 2>/dev/null
sleep 1
"$PYTHON" "\$HOME/Desktop/FileSorter/file_manager_ui.py"
LAUNCHEOF

chmod +x "$LAUNCHER"
echo "  OK  FileManager.command created"

# ── Done ───────────────────────────────────────────────────────
echo ""
echo "  +----------------------------------------------+"
echo "  |        Installation Complete!                |"
echo "  +----------------------------------------------+"
echo ""
echo "  Launch anytime: double-click FileManager.command on your Desktop"
echo "  Tip: drag it to your Dock for quick access."
echo ""
read -p "  Launch File Manager now? (Y/n): " LAUNCH
if [[ "$LAUNCH" != "n" && "$LAUNCH" != "N" ]]; then
    open "$LAUNCHER"
fi
echo ""
echo "  Press Enter to close this window."
read
