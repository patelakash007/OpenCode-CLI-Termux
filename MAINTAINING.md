# 🛡️ MAINTAINING.md — The OpenCode-CLI-Termux Guardian Manual

> **NOTICE FOR ALL FUTURE DEVELOPERS, AI ASSISTANTS, AND MAINTAINERS:**
> This repository is the result of hours of intensive low-level engineering, Bionic cross-compilation, and monorepo pruning. 
> **Read this document thoroughly before proposing, committing, or pushing any changes.**
> Never break the core principles outlined here.

---

## 1. Project Identity & Philosophy

**OpenCode-CLI-Termux** is a standalone, pure-CLI fork of OpenCode specifically engineered to run natively on **Android Termux** (ARM64 / `aarch64`).

### Core Principles (The "North Star"):
1. **100% Native Android Bionic**: Runs directly on Android's native Bionic libc. **NO PRoot, NO Ubuntu containers, NO glibc emulation layers.**
2. **Lightweight Phone Footprint**: Your phone is for running code, not melting CPU/RAM compiling heavy toolchains. All heavy compilation (Zig, Rust, Clang, Node bundling) is strictly offloaded to GitHub Actions CI.
3. **Pure CLI Only**: Zero Electron, zero web PWAs, zero Figma plugins, zero cloud serverless stacks.

---

## 2. The 7 Inviolable Laws (NEVER BREAK THESE) 🛑

### Law 1: Never Compile Heavy Binaries Locally on Phone
- **DO NOT** run `cargo build`, Zig compilations, or Node SEA bundling on your Android device. It will trigger thermal throttling, OOM (Out Of Memory) killers, or exhaust storage.
- **ALWAYS** let GitHub Actions [`.github/workflows/build-termux.yml`](.github/workflows/build-termux.yml) perform the cross-compilation in the cloud.

### Law 2: Never Do a Blind `git merge` from Upstream
- The original upstream repository (`anomalyco/opencode`) contains over **150 MB** of non-CLI bloat (Electron desktop app, SolidJS web PWA, AWS SST infra, management console).
- A blind `git merge upstream/dev` or `git pull upstream` will instantly pollute this clean repository with over 6,000 bloat files.
- **Always use selective cherry-picking** (see Section 5).

### Law 3: Protect the Bionic Shims & Patches
Never delete or bypass these critical compatibility bridges:
- **[`packages/cli/script/termux/patch-opentui.py`](packages/cli/script/termux/patch-opentui.py)**: Embeds the static `pthread_tryjoin_np` stub directly into `libopentui.so`. Without this, `node:ffi` crashes on Android Bionic with `undefined symbol: pthread_tryjoin_np`.
- **`build-termux.yml` limits.h Patch**: Isolates the Android NDK from host Ubuntu glibc headers so that Zig and Clang link against Bionic definitions.
- **`packages/cli/script/app-assets.ts` Fallback**:
  ```ts
  if (!existsSync(root)) return AppArchive.encode([])
  ```
  Ensures the CLI builds cleanly without attempting to invoke Vite for the deleted web app.

### Law 4: Never Tell Users to Run `opencode upgrade`
- Upstream's internal `opencode upgrade` command fetches prebuilt x86_64 glibc binaries from `opencode.ai`, which will crash on Android.
- **Always instruct users to update via:**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/patelakash007/OpenCode-CLI-Termux/main/install.sh | bash
  ```

### Law 5: Keep the Dependency Tree Clean
- Do not introduce dependencies that require Linux glibc, systemd, PAM, or X11/Wayland display servers.
- Any native Node native addon (`.node`) must be pre-compiled for `android-arm64` or loaded via `node:ffi`.

### Law 6: Enforce Node.js 26+ Compatibility
- This project leverages Node.js built-in `--experimental-ffi` (`node:ffi`).
- Minimum runtime requirement: **Node.js 26.x** in Termux (`pkg install nodejs`).

### Law 7: Test Before Tagging
- Before cutting a GitHub release tag (e.g. `v1.0.1`), always install the generated `.deb` package on a physical Termux device and verify:
  1. `opencode --version`
  2. `opencode stats` (verifies OpenTUI terminal rendering)
  3. `opencode run 'test'` (verifies model dispatch & PTY)

---

## 3. Codebase Map (The 21 Preserved Packages)

Only packages required for CLI and terminal UI operations are kept:

| Package Directory | Role & Purpose |
| :--- | :--- |
| `packages/cli/` | Main CLI entrypoint, command parser, arguments, and bundling scripts. |
| `packages/tui/` | Terminal User Interface (SolidJS + OpenTUI renderer, syntax highlighter). |
| `packages/core/` | Core domain engine, model providers (Anthropic, OpenAI, Gemini), tool dispatcher. |
| `packages/server/` | Local background daemon and MCP orchestrator. |
| `packages/client/` | Lightweight HTTP/IPC client communicating with the local server daemon. |
| `packages/ui/` | Audio cues (`bip-bop-01.mp3`, etc.) used by TUI attention sounds. |
| `packages/process-daemon/`| Rust PTY process helper (`opencode-pty`). |
| `packages/protocol/` | Binary and JSON wire protocols for IPC. |
| `packages/schema/` | Configuration and state validation schemas (Zod). |
| `packages/script/` | Release scripts and version metadata helpers. |
| `packages/theme/` | Terminal syntax highlighting themes. |
| `packages/ai/` | Streaming response handlers, token counting, prompt templates. |
| `packages/codemode/` | Structured code editing and diff computation engine. |
| `packages/util/` | Async helpers, string manipulation, and system utilities. |
| `packages/plugin/` | Tool and plugin subsystem. |
| `packages/plugin-browser/`| Browser execution plugin interface for subagents. |
| `packages/simulation/` | Terminal simulation test harness. |
| `packages/latex/` & `merman/`| Terminal mathematical formula and Mermaid diagram renderers. |
| `packages/http-recorder/` & `httpapi-codegen/` | API cassette testing and spec helpers. |

---

## 4. The Bionic Compatibility Secrets (Why It Works)

### A. The `pthread_tryjoin_np` Issue
- Standard Linux glibc exports `pthread_tryjoin_np`. Android's Bionic libc **does not implement it**.
- Upstream OpenTUI uses a thread pool that calls `pthread_tryjoin_np`.
- **Our Solution**: In [`patch-opentui.py`](packages/cli/script/termux/patch-opentui.py), we inject a static C stub directly into `libopentui.so` before Zig compiles it:
  ```c
  #if defined(__ANDROID__)
  int pthread_tryjoin_np(pthread_t thread, void **retval) {
      return pthread_join(thread, retval);
  }
  #endif
  ```
- This satisfies the dynamic linker without requiring any external `LD_PRELOAD` shims.

### B. The `libpthread` Bypass
- On Linux glibc, programs link with `-lpthread` and `-ldl`.
- On Android Bionic, all pthread and dl functions are embedded directly inside `libc.so`. Asking the linker for `-lpthread` causes link failure.
- In `build-termux.yml`, we instruct Zig and Clang to avoid `-lpthread` on Android target triples.

### C. NDK `<limits.h>` Isolation
- Android NDK r27 sysroot headers include `#include_next <limits.h>`.
- In standard GitHub Actions Ubuntu runners, this causes the Android compiler to accidentally pull in host Ubuntu glibc definitions (`CHAR_BIT`, `INT_MAX`), corrupting data structures.
- In `build-termux.yml`, we patch the NDK `limits.h` to supply standalone standard integer constants and eliminate the glibc leak.

---

## 5. How to Safely Pull Upstream OpenCode Features

When the original OpenCode team (`anomalyco/opencode`) adds support for new AI models or CLI features:

### Step 1: Add Upstream as a Remote (Local Only)
```bash
git remote add upstream https://github.com/anomalyco/opencode.git 2>/dev/null || true
git fetch upstream --tags
```

### Step 2: Inspect What Changed in the CLI Packages
```bash
# Check the latest 10 commits that touch core or cli
git log upstream/dev -n 10 --oneline -- packages/core packages/cli packages/tui
```

### Step 3: Selectively Cherry-Pick or Checkout
Never merge whole branches. Only bring in specific files or commits:

**Option A: Bring in a specific commit**
```bash
git cherry-pick <commit-hash>
```

**Option B: Checkout only core/cli files from a new upstream tag**
```bash
git checkout upstream/tags/vX.Y.Z -- packages/core packages/cli
```

### Step 4: Verify Local Integrity
Run a quick check to make sure no references to deleted packages (like `@opencode/desktop` or `services/*`) were accidentally imported:
```bash
git status
```

---

## 6. The Release Playbook (How to Cut a New Release)

Follow these steps exactly to ship a new version (e.g. `v1.0.1`):

1. **Bump Version**:
   - In `package.json`, set `"version": "1.0.1"`.
   - In all `packages/*/package.json`, set `"version": "1.0.1"`.
2. **Update CHANGELOG.md**:
   - Add a new section for `## [1.0.1] - YYYY-MM-DD` detailing what changed.
3. **Commit & Push to Main**:
   ```bash
   git add -A
   git commit -m "chore: v1.0.1 release"
   git push origin main
   ```
4. **Monitor GitHub Actions CI**:
   - Pushing to `main` automatically triggers `.github/workflows/build-termux.yml`.
   - Watch the build in real time:
     ```bash
     gh run watch --repo patelakash007/OpenCode-CLI-Termux --exit-status
     ```
5. **Download Generated Artifacts**:
   ```bash
   mkdir -p /tmp/release-1.0.1
   gh run download --repo patelakash007/OpenCode-CLI-Termux --dir /tmp/release-1.0.1
   ```
6. **Tag and Create GitHub Release**:
   ```bash
   git tag -a v1.0.1 -m "v1.0.1 release"
   git push origin v1.0.1
   gh release create v1.0.1 --title "v1.0.1" --notes-file CHANGELOG.md /tmp/release-1.0.1/opencode-termux-aarch64/*
   ```

---

## 7. The One-Line Installer (`install.sh`)

- The root [`install.sh`](install.sh) is the entrypoint for all users.
- It automatically queries `https://api.github.com/repos/patelakash007/OpenCode-CLI-Termux/releases/latest` to download and install the newest `.deb` via `dpkg -i`.
- Whenever you make changes to `install.sh`, test it locally with:
  ```bash
  bash -n install.sh  # Syntax check
  bash install.sh     # Dry run test
  ```

---

## 8. Emergency Troubleshooting & Diagnostics

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| `OpenTUI native FFI is not available for this runtime yet` | Node.js version is too old or `node:ffi` is disabled. | Run `pkg update && pkg install nodejs`. Verify `node -v` is 26+. |
| `undefined symbol: pthread_tryjoin_np` | `libopentui.so` was built without our Bionic patch. | Verify that `patch-opentui.py` ran before `zig build` in the CI workflow. |
| `cannot find -lpthread` | Linker tried to link Linux glibc thread library. | Remove `-lpthread` from Zig/Clang flags for Android target. |
| GitHub Actions build fails | NDK path changed or Zig dependency URL updated. | Run `gh run view <run-id> --log-failed` to view exact compiler errors. |

---

**Authored and Maintained with Pride by [patelakash007](https://github.com/patelakash007) and Antigravity (Google DeepMind).**
*Keep it light. Keep it fast. Long live native Termux.*
