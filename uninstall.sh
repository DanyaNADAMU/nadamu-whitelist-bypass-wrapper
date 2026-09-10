#!/usr/bin/env bash
#
# uninstall.sh - Uninstaller for nadamu-whitelist-bypass-wrapper
#

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo -e "\033[31m[ERROR]\033[0m Этот скрипт требует прав суперпользователя (root)." >&2
    echo "Запустите: sudo $0 $*" >&2
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
Использование: sudo ./uninstall.sh [опции]

Опции:
  --purge, -p   Удалить также каталоги конфигурации (/etc/whitelist-bypass) и пользователя whitelist-bypass
  --help, -h    Показать эту справку
USAGE_EOF
            exit 0
            ;;
        *)
            echo "Неизвестная опция: $1" >&2
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

echo -e "${C_BOLD}=== Удаление WhitelistBypass Wrapper ===${C_RESET}\n"

# 1. Stop and disable all running services
RUNNING_UNITS=$(systemctl list-units --type=service "whitelist-bypass@*.service" --no-legend 2>/dev/null | awk '{print $1}' || true)
if [[ -n "$RUNNING_UNITS" ]]; then
    log_info "Остановка служб туннелей..."
    for unit in $RUNNING_UNITS; do
        systemctl stop "$unit" 2>/dev/null || true
        systemctl disable "$unit" 2>/dev/null || true
        log_ok "Остановлен $unit"
    done
fi

# 2. Remove system files
log_info "Удаление системных файлов..."

rm -f /usr/local/bin/whitelist-bypass
log_ok "Удален /usr/local/bin/whitelist-bypass"

rm -f /etc/systemd/system/whitelist-bypass@.service
systemctl daemon-reload
log_ok "Удален /etc/systemd/system/whitelist-bypass@.service"

rm -f /etc/sudoers.d/whitelist-bypass
log_ok "Удален /etc/sudoers.d/whitelist-bypass"

rm -f /etc/bash_completion.d/whitelist-bypass
log_ok "Удален /etc/bash_completion.d/whitelist-bypass"

rm -f /usr/share/man/man1/whitelist-bypass.1
if command -v mandb >/dev/null 2>&1; then
    mandb -q 2>/dev/null || true
fi
log_ok "Удалена man-страница"

# 3. Handle data directories and service user
if [[ "$PURGE" == "true" ]]; then
    log_warn "Режим PURGE: удаление пользовательских данных и бинарников..."
    rm -rf /etc/whitelist-bypass
    rm -rf /opt/whitelist-bypass
    log_ok "Удалены /etc/whitelist-bypass и /opt/whitelist-bypass"

    if id whitelist-bypass >/dev/null 2>&1; then
        userdel -r whitelist-bypass 2>/dev/null || userdel whitelist-bypass 2>/dev/null || true
        log_ok "Удален системный пользователь whitelist-bypass"
    fi
else
    log_info "Каталог с куками и конфигами (/etc/whitelist-bypass) сохранен."
    log_info "Если вы хотите удалить все данные пользователей, запустите: sudo ./uninstall.sh --purge"
fi

echo -e "\n${C_BOLD}${C_GREEN}=== Удаление успешно завершено! ===${C_RESET}\n"
