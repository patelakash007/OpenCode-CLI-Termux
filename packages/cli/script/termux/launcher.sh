#!/data/data/com.termux/files/usr/bin/bash
# OpenCode CLI native Termux launcher (Android Bionic, ARM64)

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0")")" && pwd)"

if [ -d "$SCRIPT_DIR/../lib/assets" ]; then
  LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"
elif [ -d "$PREFIX/lib/opencode/assets" ]; then
  LIB_DIR="$PREFIX/lib/opencode"
else
  echo "Error: Cannot locate OpenCode library assets directory." >&2
  exit 1
fi

export OPENCODE_NODE_ASSETS_DIR="$LIB_DIR/assets"
export OTUI_ASSET_ROOT="$LIB_DIR/assets"
if [ -f "$LIB_DIR/assets/opencode-pty/opencode-pty" ]; then
  export OPENCODE_PTY_BIN="$LIB_DIR/assets/opencode-pty/opencode-pty"
fi

NODE_BIN="$(command -v node 2>/dev/null)"
if [ -z "$NODE_BIN" ]; then
  echo "Error: Node.js is not found. Please install it with 'pkg install nodejs'." >&2
  exit 1
fi

NODE_VER="$("$NODE_BIN" -v | sed 's/^v//' | cut -d. -f1)"
if [ "$NODE_VER" -lt 26 ] 2>/dev/null; then
  echo "Warning: OpenCode CLI requires Node 26+ for native FFI. Current version: $("$NODE_BIN" -v)" >&2
  echo "Run 'pkg update && pkg install nodejs' in Termux to upgrade to Node 26." >&2
fi

exec "$NODE_BIN" --experimental-ffi --use-system-ca --disable-warning=ExperimentalWarning "$LIB_DIR/opencode.mjs" "$@"
