#!/bin/bash
# Creates FileManager.app that shows "File Manager" in Dock

APP="$HOME/Desktop/FileManager.app"
MACOS="$APP/Contents/MacOS"
RES="$APP/Contents/Resources"

echo "Creating FileManager.app..."

# Remove old
rm -rf "$APP"

# Create structure
mkdir -p "$MACOS"
mkdir -p "$RES"

# Find Python
PYTHON=""
for P in \
    /usr/local/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if [ -x "$P" ]; then
        PYTHON="$P"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    PYTHON=$(command -v python3)
fi

echo "Using Python: $PYTHON"

# Write launcher
cat > "$MACOS/FileManager" << LAUNCHER
#!/bin/bash
lsof -ti:8765 | xargs kill -9 2>/dev/null
pkill -9 -f file_manager_ui.py 2>/dev/null
sleep 1
exec "$PYTHON" "\$HOME/Desktop/FileSorter/file_manager_ui.py"
LAUNCHER

chmod +x "$MACOS/FileManager"

# Write Info.plist
cat > "$APP/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>File Manager</string>
    <key>CFBundleDisplayName</key>
    <string>File Manager</string>
    <key>CFBundleExecutable</key>
    <string>FileManager</string>
    <key>CFBundleIdentifier</key>
    <string>com.filemanager.ui</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

# Remove quarantine
xattr -cr "$APP"

echo ""
echo "Done! FileManager.app created on Desktop."
echo ""
echo "Next:"
echo "1. Right-click FileManager.app"
echo "2. Click Open"
echo "3. Click Open on popup"
echo "4. Drag to Dock"
echo ""
