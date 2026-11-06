# OpenCode-CLI-Termux v1.0.0

> **Native OpenCode CLI for Android Termux · Bionic libc · ARM64 · No PRoot · No glibc**

---

## What this is

**OpenCode-CLI-Termux** is a lean, CLI-only fork of OpenCode specifically ported and optimized to run natively on Android Termux. It installs as a genuine Debian package (`.deb`) or standalone tarball, running directly on Android's native **Bionic libc** without needing PRoot, Ubuntu chroots, or glibc emulation layers.

---

## Requirements

- **Device**: Android 64-bit ARM (`aarch64`)
- **Environment**: Termux
- **Runtime**: Node.js 26+ (`pkg install nodejs`)

---

## Install

### One-Line Install (Recommended)
Paste this single command into Termux:
```bash
curl -fsSL https://raw.githubusercontent.com/patelakash007/OpenCode-CLI-Termux/main/install.sh | bash
```

> [!IMPORTANT]
> **How to Update**:
> To update, re-run the `install.sh` command. Do not use `opencode upgrade` — it fetches upstream, not this repo.

---

### Manual Download
You can also download the assets manually from [Releases](https://github.com/patelakash007/OpenCode-CLI-Termux/releases):

- **Debian Package**:
  ```bash
  dpkg -i opencode_2.2.5_aarch64.deb
  ```
- **Standalone Tarball**:
  ```bash
  tar -xzf opencode-termux-aarch64.tar.gz
  cd opencode-termux-aarch64
  bash install.sh
  ```

---

## Quick start

```bash
# Authenticate with your model provider
opencode auth

# Launch the interactive terminal UI
opencode

# View your coding stats and terminal activity heatmap
opencode stats

# Run a non-interactive coding prompt
opencode run 'Explain this codebase'
```

---

## What was stripped

To keep your Android device lightweight and responsive, all non-CLI bloat has been stripped from this fork:
- **14 non-CLI packages removed**: Electron desktop client (`packages/desktop`), SolidJS Web PWA (`packages/app`, `packages/web`), management console (`packages/console`), stats dashboard (`packages/stats`), storybook, session-ui, Figma plugins, SDK, etc.
- **6 non-CLI root directories removed**: `services/` (cloud backend), `salesforce/`, `infra/`, `nix/`, `sdks/`, and `specs/`.
- **23 upstream workflows removed**: Kept only the dedicated native cross-compilation pipeline.
- **Disk size impact**: Source tree reduced from **~220 MB down to 70 MB** (over 6,000 files and 1,000,000+ lines removed).

---

## How it's built

All heavy builds and cross-compilations are performed via GitHub Actions CI/CD in [`.github/workflows/build-termux.yml`](.github/workflows/build-termux.yml):
- **Android NDK r27**: C/C++ sysroot & toolchain for `aarch64-linux-android24`.
- **Zig 0.17.0**: Compiles `libopentui.so` targeting `aarch64-linux-android.24`.
- **Rust 1.90.0**: Cross-compiles `opencode-pty` session daemon for `aarch64-linux-android`.
- **Node.js 26 + `node:ffi`**: Loads native FFI bindings dynamically on device.

---

## Technical notes & Engineering Chronicle

Running OpenCode natively on Android required solving four core compatibility hurdles. For the complete technical post-mortem, problem-retry-fix matrix, and architectural case study, see **[PORTING_CHRONICLE.md](PORTING_CHRONICLE.md)**.

1. **`pthread_tryjoin_np` Stub**: Android Bionic does not export `pthread_tryjoin_np` in its C library. A static stub is embedded directly into `libopentui.so` so that dynamic loading via `node:ffi` succeeds without needing any `LD_PRELOAD` shims.
2. **`libpthread` Bypass**: Linux glibc links separate `libpthread.so` and `libdl.so`. On Android Bionic, all threading and dynamic linking primitives reside in `libc.so`. The build script skips linking `-lpthread` on Android targets.
3. **NDK `<limits.h>` Isolation**: Prevents host Linux glibc headers from leaking into Android compilation during Zig and Clang builds.
4. **Target Triple `aarch64-linux-android.24`**: Pins Android API level 24 (Android 7.0+) to guarantee maximum ABI stability on modern Termux installations.

---

## Version history

- **v1.0.0**: First standalone release. Native Bionic ARM64 build. CLI-only stripped fork. Working TUI, stats, auth, run.

---

## Maintainer Guide

For rules on how this repository is maintained, how upstream updates are safely pulled without re-introducing bloat, and the 7 inviolable laws of native Termux compilation, see [MAINTAINING.md](MAINTAINING.md).

---

## Credits

- Based on the upstream [OpenCode](https://github.com/anomalyco/opencode) project.
- Ported, stripped, and maintained for native Termux by [patelakash007](https://github.com/patelakash007).
- Built and automated with **Antigravity CLI** and **GitHub Actions**.

---

## License

[MIT](LICENSE) © 2025 OpenCode & patelakash007
