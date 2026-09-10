#!/usr/bin/env bash
#
# install.sh - Installer and updater for nadamu-whitelist-bypass-wrapper
#

set -euo pipefail

# Ensure script is run with superuser privileges
if [[ $EUID -ne 0 ]]; then
    echo -e "\033[31m[ERROR]\033[0m This script requires root privileges." >&2
    echo "Run: sudo $0 $*" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

# Bootstrap mode: when piped through curl/stdin or executed without repository files
REPO_URL="https://github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git"
REPO_SSH="git@github.com:DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git"

if [[ -z "$SCRIPT_DIR" || ! -f "$SCRIPT_DIR/bin/whitelist-bypass" || ! -f "$SCRIPT_DIR/systemd/whitelist-bypass@.service" ]]; then
    echo -e "\033[36m[INFO]\033[0m Remote execution detected. Cloning repository into a temporary directory..."

    if ! command -v git >/dev/null 2>&1; then
        echo -e "\033[31m[ERROR]\033[0m git is required for installation. Run: apt update && apt install -y git" >&2
        exit 1
    fi

    TMP_CLONE_DIR=$(mktemp -d)
    trap 'rm -rf "$TMP_CLONE_DIR"' EXIT

    CLONED=false
    AUTH_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"

    # 1. Try with provided token
    if [[ -n "$AUTH_TOKEN" ]]; then
        echo -e "\033[36m[INFO]\033[0m Authenticating via GITHUB_TOKEN..."
        if git clone --depth 1 "https://x-access-token:${AUTH_TOKEN}@github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git" "$TMP_CLONE_DIR/repo" 2>/dev/null; then
            CLONED=true
        fi
    fi

    # 2. Try anonymous public clone
    if [[ "$CLONED" != "true" ]]; then
        if git clone --depth 1 "$REPO_URL" "$TMP_CLONE_DIR/repo" 2>/dev/null; then
            CLONED=true
        fi
    fi

    # 3. Try SSH clone
    if [[ "$CLONED" != "true" ]]; then
        if git clone --depth 1 "$REPO_SSH" "$TMP_CLONE_DIR/repo" 2>/dev/null; then
            CLONED=true
        fi
    fi

    # 4. Interactive token prompt fallback
    if [[ "$CLONED" != "true" ]]; then
        echo -e "\033[33m[WARN]\033[0m Repository is private and SSH key is unavailable." >&2
        if [[ -t 0 ]]; then
            read -rsp "Enter your GitHub Personal Access Token: " USER_INPUT_TOKEN </dev/tty
            echo ""
            if git clone --depth 1 "https://x-access-token:${USER_INPUT_TOKEN}@github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git" "$TMP_CLONE_DIR/repo"; then
                CLONED=true
            fi
        fi
    fi

    if [[ "$CLONED" != "true" ]]; then
        echo -e "\033[31m[ERROR]\033[0m Failed to clone repository. Check your permissions or set GITHUB_TOKEN." >&2
        exit 1
    fi

    echo -e "\033[32m[OK]\033[0m Repository acquired successfully. Launching installation...\n"
    bash "$TMP_CLONE_DIR/repo/install.sh" "$@"
    exit 0
fi

# Configuration paths
BIN_INSTALL_PATH="/usr/local/bin/whitelist-bypass"
SYSTEMD_UNIT_PATH="/etc/systemd/system/whitelist-bypass@.service"
SUDOERS_PATH="/etc/sudoers.d/whitelist-bypass"
COMPLETION_PATH="/etc/bash_completion.d/whitelist-bypass"
MAN_PATH="/usr/share/man/man1/whitelist-bypass.1"
CONF_DIR="/etc/whitelist-bypass"
OPT_DIR="/opt/whitelist-bypass"
SERVICE_USER="whitelist-bypass"

# Text styling
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_CYAN="\033[36m"
C_YELLOW="\033[33m"

log_info() { echo -e "${C_CYAN}[INFO]${C_RESET} $*"; }
log_ok()   { echo -e "${C_GREEN}[OK]${C_RESET} $*"; }
log_warn() { echo -e "${C_YELLOW}[WARN]${C_RESET} $*"; }

BUILD_CREATORS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-creators|-b)
            BUILD_CREATORS=true
            shift
            ;;
        --help|-h)
            cat << USAGE_EOF
Usage: sudo ./install.sh [options]

Options:
  --build-creators, -b    Build fresh core binaries (headless creators) from source via Go
  --help, -h              Show this help message
USAGE_EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

echo -e "${C_BOLD}=== Installing / Updating WhitelistBypass Wrapper ===${C_RESET}\n"

# 0. Check and install optional dependencies (qrencode for terminal QR codes)
if ! command -v qrencode >/dev/null 2>&1; then
    log_info "Utility 'qrencode' not found. Installing for in-terminal QR code support..."
    if command -v apt-get >/dev/null 2>&1; then
        DEBIAN_FRONTEND=noninteractive apt-get update -qq && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq qrencode 2>/dev/null || \
            log_warn "Failed to install qrencode automatically. Please install manually: apt install -y qrencode"
    else
        log_warn "Package manager apt-get not found. Please install 'qrencode' manually."
    fi
fi

# 1. Ensure service user exists
if id "$SERVICE_USER" >/dev/null 2>&1; then
    log_info "System user '$SERVICE_USER' already exists."
else
    log_info "Creating system user '$SERVICE_USER'..."
    useradd -r -s /usr/sbin/nologin -d "$OPT_DIR" -m "$SERVICE_USER"
    log_ok "User '$SERVICE_USER' created."
fi

# 2. Prepare directory tree
log_info "Preparing directory structure..."
mkdir -p "$OPT_DIR/bin"
mkdir -p "$CONF_DIR/users"
mkdir -p /usr/share/man/man1
mkdir -p /etc/bash_completion.d

chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR" "$CONF_DIR"
chmod 700 "$CONF_DIR/users"
log_ok "Directory structure prepared."

# 3. Install or update CLI orchestrator
log_info "Installing CLI orchestrator to $BIN_INSTALL_PATH..."
cp "$SCRIPT_DIR/bin/whitelist-bypass" "$BIN_INSTALL_PATH"
chmod +x "$BIN_INSTALL_PATH"
log_ok "CLI orchestrator installed."

# 4. Install systemd unit
log_info "Installing systemd unit to $SYSTEMD_UNIT_PATH..."
cp "$SCRIPT_DIR/systemd/whitelist-bypass@.service" "$SYSTEMD_UNIT_PATH"
chmod 644 "$SYSTEMD_UNIT_PATH"
systemctl daemon-reload
log_ok "Systemd service updated and reloaded."

# 5. Install sudoers rule
log_info "Installing sudoers rule to $SUDOERS_PATH..."
cp "$SCRIPT_DIR/sudoers/whitelist-bypass" "$SUDOERS_PATH"
chmod 0440 "$SUDOERS_PATH"
log_ok "Sudoers rule configured."

# 6. Install shell completions (Bash & Zsh)
log_info "Installing Bash completions..."
mkdir -p /etc/bash_completion.d
cp "$SCRIPT_DIR/completions/bash/whitelist-bypass" "$COMPLETION_PATH"
chmod 644 "$COMPLETION_PATH"
if [[ -d /usr/share/bash-completion/completions ]]; then
    cp "$SCRIPT_DIR/completions/bash/whitelist-bypass" /usr/share/bash-completion/completions/whitelist-bypass
fi
log_ok "Bash completions installed."

log_info "Installing Zsh completions..."
mkdir -p /usr/local/share/zsh/site-functions
cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/local/share/zsh/site-functions/_whitelist-bypass
chmod 644 /usr/local/share/zsh/site-functions/_whitelist-bypass
if [[ -d /usr/share/zsh/vendor-completions ]]; then
    cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/share/zsh/vendor-completions/_whitelist-bypass
fi
if [[ -d /usr/share/zsh/site-functions ]]; then
    cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/share/zsh/site-functions/_whitelist-bypass
fi
log_ok "Zsh completions installed."

# 7. Install man page
log_info "Installing man page to $MAN_PATH..."
cp "$SCRIPT_DIR/man/whitelist-bypass.1" "$MAN_PATH"
chmod 644 "$MAN_PATH"
if command -v mandb >/dev/null 2>&1; then
    mandb -q 2>/dev/null || true
fi
log_ok "Man page installed."

# 8. Check or build creator binaries
if [[ "$BUILD_CREATORS" == "true" ]]; then
    log_info "Building fresh core binaries from GitHub master..."
    "$SCRIPT_DIR/scripts/build-latest-creators.sh" "$OPT_DIR/bin"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR/bin"
    log_ok "Core binaries built and installed."
else
    # Check if at least telemost or vk creator exists
    if [[ ! -x "$OPT_DIR/bin/headless-telemost-creator" && ! -x "$OPT_DIR/bin/headless-vk-creator" ]]; then
        log_warn "Core binaries not found in $OPT_DIR/bin."
        if command -v go >/dev/null 2>&1; then
            log_info "Go detected. Building binaries automatically..."
            "$SCRIPT_DIR/scripts/build-latest-creators.sh" "$OPT_DIR/bin"
            chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR/bin"
            log_ok "Core binaries compiled."
        else
            log_warn "Go is not installed. To build later, run: ./scripts/build-latest-creators.sh $OPT_DIR/bin"
            log_warn "Or place prebuilt binaries into $OPT_DIR/bin manually."
        fi
    fi
fi

# 9. Restart existing active services on update
ACTIVE_UNITS=$(systemctl list-units --type=service --state=running "whitelist-bypass@*.service" --no-legend 2>/dev/null | awk '{print $1}' || true)
if [[ -n "$ACTIVE_UNITS" ]]; then
    log_info "Restarting active tunnel services after update..."
    for unit in $ACTIVE_UNITS; do
        systemctl restart "$unit"
        log_ok "Restarted $unit"
    done
fi

echo -e "\n${C_BOLD}${C_GREEN}=== Installation / Update Completed Successfully! ===${C_RESET}\n"
echo "Installed components:"
echo "  • CLI utility:       $BIN_INSTALL_PATH"
echo "  • Service template:  $SYSTEMD_UNIT_PATH"
echo "  • Sudoers rule:      $SUDOERS_PATH"
echo "  • Bash completion:   $COMPLETION_PATH"
echo "  • Zsh completion:    /usr/local/share/zsh/site-functions/_whitelist-bypass"
echo "  • Man manual:        $MAN_PATH (man whitelist-bypass)"
echo "  • User configs:      $CONF_DIR/users"
echo "  • Core binaries:     $OPT_DIR/bin"
echo ""
echo "Quick status check:"
echo "  whitelist-bypass list"
echo "  whitelist-bypass qr <user>"
