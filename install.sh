#!/usr/bin/env bash
#
# install.sh - Installer and updater for nadamu-whitelist-bypass-wrapper
#

set -euo pipefail

# Ensure script is run with superuser privileges
if [[ $EUID -ne 0 ]]; then
    echo -e "\033[31m[ERROR]\033[0m Этот скрипт требует прав суперпользователя (root)." >&2
    echo "Запустите: sudo $0 $*" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
Использование: sudo ./install.sh [опции]

Опции:
  --build-creators, -b    Собрать свежие бинарники ядра (headless creators) из исходников через Go
  --help, -h              Показать эту справку
USAGE_EOF
            exit 0
            ;;
        *)
            echo "Неизвестная опция: $1" >&2
            exit 1
            ;;
    esac
done

echo -e "${C_BOLD}=== Установка / Обновление WhitelistBypass Wrapper ===${C_RESET}\n"

# 1. Ensure service user exists
if id "$SERVICE_USER" >/dev/null 2>&1; then
    log_info "Системный пользователь '$SERVICE_USER' уже существует."
else
    log_info "Создание системного пользователя '$SERVICE_USER'..."
    useradd -r -s /usr/sbin/nologin -d "$OPT_DIR" -m "$SERVICE_USER"
    log_ok "Пользователь '$SERVICE_USER' создан."
fi

# 2. Prepare directory tree
log_info "Подготовка структуры каталогов..."
mkdir -p "$OPT_DIR/bin"
mkdir -p "$CONF_DIR/users"
mkdir -p /usr/share/man/man1
mkdir -p /etc/bash_completion.d

chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR" "$CONF_DIR"
chmod 700 "$CONF_DIR/users"
log_ok "Каталоги подготовлены."

# 3. Install or update CLI orchestrator
log_info "Установка CLI-оркестратора в $BIN_INSTALL_PATH..."
cp "$SCRIPT_DIR/bin/whitelist-bypass" "$BIN_INSTALL_PATH"
chmod +x "$BIN_INSTALL_PATH"
log_ok "CLI-оркестратор установлен."

# 4. Install systemd unit
log_info "Установка службы systemd в $SYSTEMD_UNIT_PATH..."
cp "$SCRIPT_DIR/systemd/whitelist-bypass@.service" "$SYSTEMD_UNIT_PATH"
chmod 644 "$SYSTEMD_UNIT_PATH"
systemctl daemon-reload
log_ok "Служба systemd обновлена и перезагружена."

# 5. Install sudoers rule
log_info "Установка правила sudoers в $SUDOERS_PATH..."
cp "$SCRIPT_DIR/sudoers/whitelist-bypass" "$SUDOERS_PATH"
chmod 0440 "$SUDOERS_PATH"
log_ok "Правило sudoers настроено."

# 6. Install shell completions (Bash & Zsh)
log_info "Установка автодополнения для Bash..."
mkdir -p /etc/bash_completion.d
cp "$SCRIPT_DIR/completions/bash/whitelist-bypass" "$COMPLETION_PATH"
chmod 644 "$COMPLETION_PATH"
if [[ -d /usr/share/bash-completion/completions ]]; then
    cp "$SCRIPT_DIR/completions/bash/whitelist-bypass" /usr/share/bash-completion/completions/whitelist-bypass
fi
log_ok "Автодополнение Bash установлено."

log_info "Установка автодополнения для Zsh..."
mkdir -p /usr/local/share/zsh/site-functions
cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/local/share/zsh/site-functions/_whitelist-bypass
chmod 644 /usr/local/share/zsh/site-functions/_whitelist-bypass
if [[ -d /usr/share/zsh/vendor-completions ]]; then
    cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/share/zsh/vendor-completions/_whitelist-bypass
fi
if [[ -d /usr/share/zsh/site-functions ]]; then
    cp "$SCRIPT_DIR/completions/zsh/_whitelist-bypass" /usr/share/zsh/site-functions/_whitelist-bypass
fi
log_ok "Автодополнение Zsh установлено."

# 7. Install man page
log_info "Установка man-страницы в $MAN_PATH..."
cp "$SCRIPT_DIR/man/whitelist-bypass.1" "$MAN_PATH"
chmod 644 "$MAN_PATH"
if command -v mandb >/dev/null 2>&1; then
    mandb -q 2>/dev/null || true
fi
log_ok "Страница man установлена."

# 8. Check or build creator binaries
if [[ "$BUILD_CREATORS" == "true" ]]; then
    log_info "Сборка свежих бинарников ядра из GitHub..."
    "$SCRIPT_DIR/scripts/build-latest-creators.sh" "$OPT_DIR/bin"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR/bin"
    log_ok "Бинарники ядра успешно собраны и установлены."
else
    # Check if at least telemost or vk creator exists
    if [[ ! -x "$OPT_DIR/bin/headless-telemost-creator" && ! -x "$OPT_DIR/bin/headless-vk-creator" ]]; then
        log_warn "Бинарники ядра в $OPT_DIR/bin не найдены."
        if command -v go >/dev/null 2>&1; then
            log_info "Найден Go. Автоматическая сборка бинарников..."
            "$SCRIPT_DIR/scripts/build-latest-creators.sh" "$OPT_DIR/bin"
            chown -R "$SERVICE_USER:$SERVICE_USER" "$OPT_DIR/bin"
            log_ok "Бинарники ядра собраны."
        else
            log_warn "Go не установлен. Для сборки запустите позже: ./scripts/build-latest-creators.sh $OPT_DIR/bin"
            log_warn "Или поместите готовые бинарники в $OPT_DIR/bin вручную."
        fi
    fi
fi

# 9. Restart existing active services on update
ACTIVE_UNITS=$(systemctl list-units --type=service --state=running "whitelist-bypass@*.service" --no-legend 2>/dev/null | awk '{print $1}' || true)
if [[ -n "$ACTIVE_UNITS" ]]; then
    log_info "Перезапуск активных туннелей после обновления..."
    for unit in $ACTIVE_UNITS; do
        systemctl restart "$unit"
        log_ok "Перезапущен $unit"
    done
fi

echo -e "\n${C_BOLD}${C_GREEN}=== Установка / Обновление успешно завершена! ===${C_RESET}\n"
echo "Установленные компоненты:"
echo "  • CLI утилита:     $BIN_INSTALL_PATH"
echo "  • Шаблон службы:   $SYSTEMD_UNIT_PATH"
echo "  • Правило sudoers: $SUDOERS_PATH"
echo "  • Автодополнение:  $COMPLETION_PATH"
echo "  • Man-руководство: $MAN_PATH (man whitelist-bypass)"
echo "  • Каталог данных:  $CONF_DIR/users"
echo "  • Каталог бинарников: $OPT_DIR/bin"
echo ""
echo "Быстрая проверка пользователей:"
echo "  whitelist-bypass list"
