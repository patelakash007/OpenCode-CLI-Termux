#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
DIST="$ROOT_DIR/dist-termux"
OUT="$ROOT_DIR/release-artifacts"
VERSION="${OPENCODE_VERSION:-1.0.0}"

echo "=== Assembling Termux Package Structure ==="
rm -rf "$DIST" "$OUT"
mkdir -p "$DIST/bin" "$DIST/lib/assets" "$OUT"

# 1. Copy bundled JS entrypoint
cp -v "$ROOT_DIR/packages/cli/dist-node/opencode.mjs" "$DIST/lib/opencode.mjs"

# 2. Copy staged assets from dist-node
cp -r "$ROOT_DIR/packages/cli/dist-node/assets/"* "$DIST/lib/assets/"

# 3. Clean up non-Bionic / glibc native modules copied from dist-node
rm -rf "$DIST/lib/assets/@parcel"
rm -rf "$DIST/lib/assets/@ff-labs"
rm -rf "$DIST/lib/assets/@yuuang"

# 4. Inject Bionic Android libopentui.so
if [ -f "$ROOT_DIR/.build-termux/opentui/libopentui.so" ]; then
  OTUI_DIR="$DIST/lib/assets/@opentui/core-linux-arm64"
  mkdir -p "$OTUI_DIR"
  cp -v "$ROOT_DIR/.build-termux/opentui/libopentui.so" "$OTUI_DIR/libopentui.so"
else
  echo "Error: libopentui.so not found in .build-termux/opentui!"
  exit 1
fi

# 5. Inject Bionic Android pty.node into all possible lookup locations
if [ -f "$ROOT_DIR/.build-termux/pty-node/package/prebuilds/android-arm64/pty.node" ]; then
  PTY_BIONIC="$ROOT_DIR/.build-termux/pty-node/package/prebuilds/android-arm64/pty.node"
  PTY_BASE="$DIST/lib/assets/@lydell/node-pty-linux-arm64"
  mkdir -p "$PTY_BASE/build/Release" "$PTY_BASE/prebuilds/linux-arm64" "$PTY_BASE/prebuilds/android-arm64"
  cp -v "$PTY_BIONIC" "$PTY_BASE/build/Release/pty.node"
  cp -v "$PTY_BIONIC" "$PTY_BASE/prebuilds/linux-arm64/pty.node"
  cp -v "$PTY_BIONIC" "$PTY_BASE/prebuilds/android-arm64/pty.node"
else
  echo "Error: Bionic pty.node not found in .build-termux/pty-node!"
  exit 1
fi

# 6. Inject opencode-pty if compiled, otherwise remove glibc copy
if [ -f "$ROOT_DIR/.build-termux/pty/opencode-pty" ]; then
  mkdir -p "$DIST/lib/assets/opencode-pty"
  cp -v "$ROOT_DIR/.build-termux/pty/opencode-pty" "$DIST/lib/assets/opencode-pty/opencode-pty"
  chmod 755 "$DIST/lib/assets/opencode-pty/opencode-pty"
else
  echo "opencode-pty not compiled for Bionic; removing glibc copy and relying on Bionic node-pty"
  rm -rf "$DIST/lib/assets/opencode-pty"
fi

# 7. Copy launcher and installer
cp -v "$ROOT_DIR/packages/cli/script/termux/launcher.sh" "$DIST/bin/opencode"
chmod 755 "$DIST/bin/opencode"

cp -v "$ROOT_DIR/packages/cli/script/termux/install.sh" "$DIST/install.sh"
chmod 755 "$DIST/install.sh"

echo "=== Verifying ELF dependencies (NO glibc allowed) ==="
find "$DIST" -type f \( -name "*.so" -o -name "*.node" -o -name "opencode-pty" \) | while read -r file; do
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
Homepage: https://github.com/patelakash007/OpenCode-CLI-Termux
Description: OpenCode AI CLI for native Termux (Bionic libc, ARM64, no PRoot)
EOF

dpkg-deb --build --root-owner-group "$DEB_DIR" "$OUT/opencode_${VERSION}_aarch64.deb"
ls -la "$OUT"
