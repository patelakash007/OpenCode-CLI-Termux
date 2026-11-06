#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
DIST="$ROOT_DIR/dist-termux"
OUT="$ROOT_DIR/release-artifacts"
VERSION="2.2.5"

echo "=== Assembling Termux Package Structure ==="
rm -rf "$DIST" "$OUT"
mkdir -p "$DIST/bin" "$DIST/lib/assets" "$OUT"

# 1. Copy bundled JS entrypoint
cp -v "$ROOT_DIR/packages/cli/dist-node/opencode.mjs" "$DIST/lib/opencode.mjs"

# 2. Copy staged assets from dist-node
cp -r "$ROOT_DIR/packages/cli/dist-node/assets/"* "$DIST/lib/assets/"

# 3. Inject Bionic Android libopentui.so
if [ -f "$ROOT_DIR/.build-termux/opentui/libopentui.so" ]; then
  OTUI_DIR="$DIST/lib/assets/@opentui/core-linux-arm64"
  mkdir -p "$OTUI_DIR"
  cp -v "$ROOT_DIR/.build-termux/opentui/libopentui.so" "$OTUI_DIR/libopentui.so"
fi

# 4. Inject Bionic Android pty.node
if [ -f "$ROOT_DIR/.build-termux/pty-node/package/prebuilds/android-arm64/pty.node" ]; then
  PTY_NODE_DIR="$DIST/lib/assets/@lydell/node-pty-linux-arm64/build/Release"
  mkdir -p "$PTY_NODE_DIR" "$DIST/lib/assets/@lydell/node-pty-linux-arm64/prebuilds/android-arm64"
  cp -v "$ROOT_DIR/.build-termux/pty-node/package/prebuilds/android-arm64/pty.node" "$PTY_NODE_DIR/pty.node"
  cp -v "$ROOT_DIR/.build-termux/pty-node/package/prebuilds/android-arm64/pty.node" "$DIST/lib/assets/@lydell/node-pty-linux-arm64/prebuilds/android-arm64/pty.node"
fi

# 5. Inject opencode-pty if compiled
if [ -f "$ROOT_DIR/.build-termux/pty/opencode-pty" ]; then
  mkdir -p "$DIST/lib/assets/opencode-pty"
  cp -v "$ROOT_DIR/.build-termux/pty/opencode-pty" "$DIST/lib/assets/opencode-pty/opencode-pty"
  chmod 755 "$DIST/lib/assets/opencode-pty/opencode-pty"
fi

# 6. Copy launcher and installer
cp -v "$ROOT_DIR/packages/cli/script/termux/launcher.sh" "$DIST/bin/opencode"
chmod 755 "$DIST/bin/opencode"

cp -v "$ROOT_DIR/packages/cli/script/termux/install.sh" "$DIST/install.sh"
chmod 755 "$DIST/install.sh"

echo "=== Verifying ELF dependencies (NO glibc allowed) ==="
for file in $(find "$DIST" -name "*.so" -o -name "*.node" -o -name "opencode-pty"); do
  echo "--- $file ---"
  readelf -d "$file" | grep -E 'NEEDED|RUNPATH' || true
  if readelf -d "$file" | grep -i 'libc\.so\.6'; then
    echo "FATAL: glibc detected in $file!"
    exit 1
  fi
done
echo "All native libraries verified: Pure Android Bionic linkage!"

echo "=== Packaging tar.gz ==="
tar -czvf "$OUT/opencode-termux-aarch64.tar.gz" -C "$DIST" .

echo "=== Packaging .deb ==="
DEB_DIR="/tmp/opencode-deb"
rm -rf "$DEB_DIR"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/data/data/com.termux/files/usr/bin"
mkdir -p "$DEB_DIR/data/data/com.termux/files/usr/lib/opencode"

cp -r "$DIST/bin/opencode" "$DEB_DIR/data/data/com.termux/files/usr/bin/"
cp -r "$DIST/lib/"* "$DEB_DIR/data/data/com.termux/files/usr/lib/opencode/"
chmod 755 "$DEB_DIR/data/data/com.termux/files/usr/bin/opencode"

cat << EOF > "$DEB_DIR/DEBIAN/control"
Package: opencode
Version: ${VERSION}
Architecture: aarch64
Maintainer: patelakash007
Depends: nodejs (>= 26.0.0)
Section: utils
Priority: optional
Homepage: https://github.com/patelakash007/OpenCode-CLI
Description: OpenCode AI CLI for native Termux (Bionic libc, ARM64, no PRoot)
EOF

dpkg-deb --build --root-owner-group "$DEB_DIR" "$OUT/opencode_${VERSION}_aarch64.deb"
ls -la "$OUT"
