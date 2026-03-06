#!/usr/bin/env bash
set -euo pipefail

# ── Optra Installer ──────────────────────────────────────────
# Usage: curl -sSL https://raw.githubusercontent.com/RyaninKR/optra/main/install.sh | bash

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

info()  { echo -e "${BOLD}${GREEN}[optra]${RESET} $1"; }
warn()  { echo -e "${BOLD}${YELLOW}[optra]${RESET} $1"; }
error() { echo -e "${BOLD}${RED}[optra]${RESET} $1"; exit 1; }

# ── 1. Python 확인 ──
check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        error "Python 3.11+ is required but not found.\n  macOS:  brew install python\n  Linux:  sudo apt install python3 python3-venv"
    fi

    VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
    MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

    if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
        error "Python 3.11+ is required (found $VERSION)"
    fi

    info "Found Python $VERSION"
}

# ── 2. pipx 확인 및 설치 ──
ensure_pipx() {
    if command -v pipx &>/dev/null; then
        info "Found pipx"
        return
    fi

    warn "pipx not found. Installing..."

    if command -v brew &>/dev/null; then
        brew install pipx
    elif command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y pipx
    else
        $PYTHON -m pip install --user pipx
    fi

    # Ensure pipx bin dir is on PATH
    pipx ensurepath 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v pipx &>/dev/null; then
        error "Failed to install pipx. Please install it manually: https://pipx.pypa.io/stable/installation/"
    fi

    info "pipx installed"
}

# ── 3. optra 설치 ──
install_optra() {
    if command -v optra &>/dev/null; then
        warn "optra is already installed. Upgrading..."
        pipx upgrade optra || pipx install --force optra
    else
        info "Installing optra..."
        pipx install optra
    fi
}

# ── 4. 검증 ──
verify() {
    if command -v optra &>/dev/null; then
        echo ""
        info "Installation complete!"
        echo ""
        echo -e "  Get started:"
        echo -e "    ${BOLD}optra auth slack${RESET}    Connect Slack"
        echo -e "    ${BOLD}optra auth notion${RESET}   Connect Notion"
        echo -e "    ${BOLD}optra collect${RESET}       Collect work history"
        echo -e "    ${BOLD}optra summary${RESET}       Generate daily summary"
        echo ""
    else
        warn "optra was installed but is not on PATH."
        echo -e "  Try: ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
        echo -e "  Then restart your terminal."
    fi
}

# ── Main ──
echo ""
echo -e "${BOLD}  Optra Installer${RESET}"
echo -e "  Aggregate your work history from Slack, Notion, and more"
echo ""

check_python
ensure_pipx
install_optra
verify
