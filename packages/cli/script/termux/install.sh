#!/data/data/com.termux/files/usr/bin/bash
set -e
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing OpenCode CLI to $PREFIX ==="
mkdir -p "$PREFIX/bin" "$PREFIX/lib/opencode"

cp -rf "$SCRIPT_DIR/lib/"* "$PREFIX/lib/opencode/"
cp -f "$SCRIPT_DIR/bin/opencode" "$PREFIX/bin/opencode"
chmod 755 "$PREFIX/bin/opencode"
chmod -R 755 "$PREFIX/lib/opencode/assets" 2>/dev/null || true

echo "OpenCode CLI installed successfully!"
echo "Run 'opencode --help' or 'opencode' to start."
