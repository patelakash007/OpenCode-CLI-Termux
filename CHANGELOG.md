# Changelog

All notable changes to **OpenCode-CLI-Termux** are documented here.

## [1.0.0] - 2026-11-07

### Added
- First standalone release of **OpenCode-CLI-Termux**.
- Native Bionic ARM64 build running without PRoot or glibc shims.
- Working terminal user interface (OpenTUI), stats heatmap, provider auth, and non-interactive `opencode run`.
- Fully automated GitHub Actions cross-compilation pipeline producing both `.deb` package and `.tar.gz` distribution.

### Changed
- CLI-only stripped fork: pruned 14 non-CLI packages (Electron desktop app, Web PWA, console, stats).
- Pruned 6 cloud services and infra directories (`services/`, `salesforce/`, `infra/`, `nix/`, `sdks/`, `specs/`).
- Reduced source tree size by ~68% (from 220MB down to 70MB).
