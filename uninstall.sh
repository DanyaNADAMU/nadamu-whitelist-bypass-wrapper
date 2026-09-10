#!/usr/bin/env bash
#
# uninstall.sh - Uninstaller for nadamu-whitelist-bypass-wrapper
#

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo -e "\033[31m[ERROR]\033[0m This script requires root privileges." >&2
    echo "Run: sudo $0 $*" >&2
    exit 1
fi

PURGE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge|-p)
            PURGE=true
            shift
            ;;
        --help|-h)
            cat << USAGE_EOF
Usage: sudo ./uninstall.sh [options]

Options:
  --purge, -p   Purge configuration directories (/etc/whitelist-bypass) and system user
  --help, -h    Show this help message
USAGE_EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[32m"
C_RED="\033[31m"
C_CYAN="\033[36m"
C_YELLOW="\033[33m"

log_info() { echo -e "${C_CYAN}[INFO]${C_RESET} $*"; }
log_ok()   { echo -e "${C_GREEN}[OK]${C_RESET} $*"; }
log_warn() { echo -e "${C_YELLOW}[WARN]${C_RESET} $*"; }

echo -e "${C_BOLD}=== Uninstalling WhitelistBypass Wrapper ===${C_RESET}\n"

# 1. Stop and disable all running services
RUNNING_UNITS=$(systemctl list-units --type=service "whitelist-bypass@*.service" --no-legend 2>/dev/null | awk '{print $1}' || true)
if [[ -n "$RUNNING_UNITS" ]]; then
    log_info "Stopping active tunnel services..."
    for unit in $RUNNING_UNITS; do
        systemctl stop "$unit" 2>/dev/null || true
        systemctl disable "$unit" 2>/dev/null || true
        log_ok "Stopped $unit"
    done
fi

for daemon in whitelist-bypass-telegram-bot.service whitelist-bypass-vk-bot.service whitelist-bypass-core.service; do
    if systemctl is-active "$daemon" >/dev/null 2>&1 || systemctl is-enabled "$daemon" >/dev/null 2>&1; then
        log_info "Stopping and disabling $daemon..."
        systemctl stop "$daemon" 2>/dev/null || true
        systemctl disable "$daemon" 2>/dev/null || true
        log_ok "Stopped $daemon"
    fi
done

# 2. Remove system files
log_info "Removing system files..."

rm -f /usr/local/bin/whitelist-bypass
log_ok "Removed /usr/local/bin/whitelist-bypass"

rm -f /etc/systemd/system/whitelist-bypass@.service
rm -f /etc/systemd/system/whitelist-bypass-core.service
rm -f /etc/systemd/system/whitelist-bypass-telegram-bot.service
rm -f /etc/systemd/system/whitelist-bypass-vk-bot.service
systemctl daemon-reload
log_ok "Removed systemd service units"

rm -f /etc/sudoers.d/whitelist-bypass
log_ok "Removed /etc/sudoers.d/whitelist-bypass"

rm -f /etc/bash_completion.d/whitelist-bypass
rm -f /usr/share/bash-completion/completions/whitelist-bypass
rm -f /usr/local/share/zsh/site-functions/_whitelist-bypass
rm -f /usr/share/zsh/vendor-completions/_whitelist-bypass
rm -f /usr/share/zsh/site-functions/_whitelist-bypass
log_ok "Removed Bash and Zsh shell completions"

rm -f /usr/share/man/man1/whitelist-bypass.1
if command -v mandb >/dev/null 2>&1; then
    mandb -q 2>/dev/null || true
fi
log_ok "Removed man page"

# 3. Handle data directories and service user
if [[ "$PURGE" == "true" ]]; then
    log_warn "PURGE mode active: removing user data and core binaries..."
    rm -rf /etc/whitelist-bypass
    rm -rf /opt/whitelist-bypass
    log_ok "Removed /etc/whitelist-bypass and /opt/whitelist-bypass"

    if id whitelist-bypass >/dev/null 2>&1; then
        userdel -r whitelist-bypass 2>/dev/null || userdel whitelist-bypass 2>/dev/null || true
        log_ok "Removed system user whitelist-bypass"
    fi
else
    log_info "Configuration directory (/etc/whitelist-bypass) preserved."
    log_info "To purge all user data, re-run with: sudo ./uninstall.sh --purge"
fi

echo -e "\n${C_BOLD}${C_GREEN}=== Uninstallation Completed Successfully! ===${C_RESET}\n"
