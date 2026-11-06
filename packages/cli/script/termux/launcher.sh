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

NODE_FLAGS=()
if "$NODE_BIN" --help 2>&1 | grep -q -- '--experimental-ffi'; then
  NODE_FLAGS+=("--experimental-ffi")
fi
if "$NODE_BIN" --help 2>&1 | grep -q -- '--use-system-ca'; then
  NODE_FLAGS+=("--use-system-ca")
fi
if "$NODE_BIN" --help 2>&1 | grep -q -- '--disable-warning'; then
  NODE_FLAGS+=("--disable-warning=ExperimentalWarning")
fi

exec "$NODE_BIN" "${NODE_FLAGS[@]}" "$LIB_DIR/opencode.mjs" "$@"
