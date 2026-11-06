#!/usr/bin/env bash
# ==============================================================================
# OpenCode-CLI-Termux Installer
# Native OpenCode CLI for Android Termux (Bionic libc, ARM64, no PRoot)
# Repository: https://github.com/patelakash007/OpenCode-CLI-Termux
# ==============================================================================

set -euo pipefail

# Terminal colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}=== OpenCode-CLI-Termux Installer ===${NC}"

# 1. Environment & Architecture Checks
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "arm64" ]; then
    echo -e "${RED}Error: Unsupported architecture: $ARCH${NC}"
    echo "OpenCode-CLI-Termux requires a 64-bit ARM device (aarch64/arm64)."
    exit 1
fi

if [ -z "${PREFIX:-}" ] || [ ! -d "$PREFIX" ]; then
    echo -e "${YELLOW}Warning: PREFIX environment variable is not set. Assuming standard Termux path...${NC}"
    PREFIX="/data/data/com.termux/files/usr"
fi

# 2. Check Prerequisites
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${YELLOW}curl not found. Installing curl via pkg...${NC}"
    pkg install -y curl
fi

if ! command -v node >/dev/null 2>&1; then
    echo -e "${YELLOW}Node.js not found. Installing nodejs via pkg...${NC}"
    pkg install -y nodejs
else
    NODE_VERSION=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
        echo -e "${YELLOW}Node.js version $NODE_VERSION detected. Node.js 22+ (preferably 26+) is recommended.${NC}"
        echo -e "${YELLOW}Run 'pkg update && pkg install nodejs' if you encounter any runtime issues.${NC}"
    fi
fi

# 3. Locate Latest Release
REPO="patelakash007/OpenCode-CLI-Termux"
echo -e "${BLUE}Fetching latest release info from GitHub...${NC}"

LATEST_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null || true)
DEB_URL=""

if [ -n "$LATEST_JSON" ]; then
    DEB_URL=$(echo "$LATEST_JSON" | grep -o 'https://[^"]*aarch64\.deb' | head -n 1 || true)
fi

# Fallback URL if GitHub API rate-limited or fails
if [ -z "$DEB_URL" ]; then
    DEB_URL="https://github.com/$REPO/releases/latest/download/opencode_2.2.5_aarch64.deb"
fi

echo -e "Target package: ${BOLD}$DEB_URL${NC}"

# 4. Download .deb package
TMP_DIR="${PREFIX}/tmp"
mkdir -p "$TMP_DIR"
DEB_FILE="$TMP_DIR/opencode_termux_latest.deb"

echo -e "${BLUE}Downloading package...${NC}"
curl -# -L -o "$DEB_FILE" "$DEB_URL"

# 5. Install via dpkg
echo -e "${BLUE}Installing OpenCode CLI...${NC}"
dpkg -i "$DEB_FILE"

# Clean up temporary download
rm -f "$DEB_FILE"

# 6. Verification & Done
echo ""
echo -e "${GREEN}${BOLD}✓ OpenCode-CLI-Termux installed successfully!${NC}"
if command -v opencode >/dev/null 2>&1; then
    echo -e "Installed version: ${BOLD}$(opencode --version 2>/dev/null || echo 'v1.0.0')${NC}"
fi

echo ""
echo -e "${BOLD}Quick Start:${NC}"
echo -e "  ${GREEN}opencode auth${NC}    # Configure your AI model API keys"
echo -e "  ${GREEN}opencode${NC}         # Launch the interactive terminal UI"
echo -e "  ${GREEN}opencode stats${NC}   # View your coding stats heatmap"
echo ""
echo -e "${YELLOW}${BOLD}Notice on Updates:${NC}"
echo -e "  To update, re-run this install command:"
echo -e "  ${BOLD}curl -fsSL https://raw.githubusercontent.com/patelakash007/OpenCode-CLI-Termux/main/install.sh | bash${NC}"
echo -e "  ${RED}Do not use 'opencode upgrade'${NC} — it fetches upstream, not this repo."
echo ""
