#!/usr/bin/env sh
# Build a lightweight ROAR AppImage launcher.
# The produced AppImage expects to live under $ROAR_HOME/bin.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROAR_HOME=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
APPDIR="$ROAR_HOME/.appimage-build/AppDir"
OUTPUT="$ROAR_HOME/bin/ROAR-$(uname -m).AppImage"

APPIMAGETOOL_BIN="${APPIMAGETOOL:-}"
if [ -n "$APPIMAGETOOL_BIN" ]; then
    if [ ! -x "$APPIMAGETOOL_BIN" ]; then
        echo "APPIMAGETOOL is set but is not executable: $APPIMAGETOOL_BIN" >&2
        exit 1
    fi
else
    APPIMAGETOOL_BIN=$(command -v appimagetool || true)
fi

if [ -z "$APPIMAGETOOL_BIN" ]; then
    echo "appimagetool is required but was not found in PATH." >&2
    echo "Either install it or run: APPIMAGETOOL=/path/to/appimagetool $0" >&2
    exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env sh
set -eu

if [ -n "${APPIMAGE:-}" ]; then
    APPIMAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$APPIMAGE")" && pwd)
    export ROAR_HOME="${ROAR_HOME:-$APPIMAGE_DIR/..}"
fi

exec "$ROAR_HOME/bin/roar" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/roar.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=ROAR
Comment=Launch the ROAR analog design GUI
Exec=roar
Icon=roar
Terminal=false
Categories=Development;Electronics;
StartupNotify=true
StartupWMClass=ROAR
EOF

cp "$ROAR_HOME/images/png/ROAR_ICON.png" "$APPDIR/roar.png"
cp "$ROAR_HOME/images/png/ROAR_ICON.png" "$APPDIR/.DirIcon"
cp "$ROAR_HOME/images/png/ROAR_ICON.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/roar.png"
cp "$APPDIR/roar.desktop" "$APPDIR/usr/share/applications/roar.desktop"

"$APPIMAGETOOL_BIN" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"

echo "Created: $OUTPUT"

