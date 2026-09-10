# nadamu-whitelist-bypass-wrapper

[English version](README.md) | **Русская версия**

Мульти-аккаунтная серверная обертка и диспетчер для [kulikov0/whitelist-bypass](https://github.com/kulikov0/whitelist-bypass).

Решает задачу туннелирования интернет-трафика (L4-over-WebRTC) через медиа-серверы российских сервисов (Яндекс.Телемост, VK Звонки, WB Stream, DION) в условиях строгих белых списков операторов связи.

---

## Ключевые возможности

- **Строгая изоляция 1:1:1:** 1 пользователь = 1 сервисный аккаунт (cookies) = 1 активная комната = 1 изолированный headless-creator.
- **Локальный API и Systemd-ядро:** фоновый демон `whitelist-bypass-core.service` с REST API через Unix Domain Socket (`/run/whitelist-bypass/core.sock`).
- **Единый реестр команд:** абсолютно одинаковый синтаксис команд и структурированный вывод `--json` для CLI, Telegram/VK ботов и веб-панелей.
- **Поддержка всех провайдеров:** Яндекс.Телемост, VK Звонки, WB Stream, DION через единый интерфейс.
- **Мгновенное переключение:** команда `whitelist-bypass provider <user> <provider> [--rotate]` для бесшовной смены платформы без ручного редактирования файлов.
- **QR-коды прямо в терминале:** команда `whitelist-bypass qr <user>` с автоматической адаптацией к темным темам и ширине терминала.
- **Надежная ротация комнат:** автоматическая генерация и фиксация ссылок через флаг ядра `--write-file` без таймаутных костылей (`sleep`).
- **Управление через systemd:** шаблонизированный изолированный сервис `whitelist-bypass@<username>.service` с жесткими ограничениями безопасности (`ProtectSystem=strict`, `NoNewPrivileges=true`).
- **Бесперебойный fallback:** CLI-утилита работает надежно как при запущенном ядре, так и в режиме прямого in-process исполнения при остановленном демоне.

---

## Структура репозитория

```text
.
├── bin/
│   └── whitelist-bypass             # Единый исполняемый CLI-скрипт
├── core/                            # Python-ядро и локальный API
│   ├── app.py                       # Сервер FastAPI REST API / UDS
│   ├── client.py                    # Клиентская библиотека с фоллбэком
│   ├── commands.py                  # Единый реестр команд
│   ├── config.py                    # Конфигурация и пути системы
│   ├── models.py                    # Модели данных и типизация
│   └── services/                    # Сервисный слой
│       ├── qr_service.py            # Генератор ANSI и Base64 QR-кодов
│       ├── tunnel_service.py        # Супервизор systemd и ротатор комнат
│       └── user_service.py          # Профили пользователей и валидация cookies
├── systemd/
│   ├── whitelist-bypass-core.service# Служба демона ядра
│   └── whitelist-bypass@.service    # Шаблон службы для туннелей пользователей
├── sudoers/
│   └── whitelist-bypass             # Правило sudoers для служебного пользователя
├── completions/
│   ├── bash/whitelist-bypass        # Автодополнение для Bash
│   └── zsh/_whitelist-bypass        # Автодополнение для Zsh
├── man/
│   └── whitelist-bypass.1           # Руководство man (man whitelist-bypass)
├── examples/
│   ├── user.conf.example            # Пример файла конфигурации пользователя
│   └── room.env.example             # Пример файла сохраненной ссылки
├── docs/
│   ├── en/                          # Документация на английском языке
│   └── ru/                          # Документация на русском языке
│       ├── SETUP.md                 # Пошаговая инструкция по установке
│       └── CLIENT_ANDROID.md        # Настройка клиента Android
├── requirements.txt                 # Зависимости Python для демона ядра
├── install.sh                       # Идемпотентный инсталлятор / апдейтер
├── uninstall.sh                     # Скрипт удаления
└── PLAN.md                          # Архитектурный план и этапы разработки
```

---

## Быстрая установка в одну команду (curl)

**Когда репозиторий публичный:**
```bash
curl -fsSL https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo bash -s -- --build-creators
```

**Пока репозиторий приватный:**
```bash
# Передайте ваш GitHub Personal Access Token (PAT):
curl -fsSL -H "Authorization: token $GITHUB_TOKEN" https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo GITHUB_TOKEN=$GITHUB_TOKEN bash -s -- --build-creators
```

---

## Установка и обновление из локальной копии

```bash
git clone https://github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git
cd nadamu-whitelist-bypass-wrapper

sudo ./install.sh --build-creators
```

Инсталлятор:
- Создает изолированного системного пользователя `whitelist-bypass`
- Устанавливает утилиту в `/usr/local/bin/whitelist-bypass`
- Регистрирует службу `whitelist-bypass@.service` в systemd
- Настраивает беспарольные права sudoers
- Подключает автодополнение Bash/Zsh и man-страницу
- Проверяет наличие `qrencode` для генерации QR-кодов
- Автоматически собирает свежие бинарники ядра без багов дисконнекта

Для **обновления** достаточно выполнить:
```bash
git pull
sudo ./install.sh
```

Для **удаления**:
```bash
sudo ./uninstall.sh          # Сохраняет куки и данные пользователей
sudo ./uninstall.sh --purge  # Полная очистка с данными
```

---

## Базовые команды управления

```bash
# Показать список пользователей и их статус
whitelist-bypass list

# Создать новую чистую комнату для пользователя (с выводом QR-кода)
whitelist-bypass rotate <username> --qr

# Получить текущую ссылку пользователя
whitelist-bypass get-link <username>
whitelist-bypass get-link <username> --qr

# Быстрый вывод QR-кода ссылки в терминале для мобильного клиента
whitelist-bypass qr <username>

# Смена платформы/провайдера (telemost, vk, wbstream, dion)
whitelist-bypass set-provider <username> vk --rotate

# Управление службой
whitelist-bypass start <username>
whitelist-bypass stop <username>
whitelist-bypass status <username>
```

Подробное руководство по развертыванию доступно в [docs/ru/SETUP.md](docs/ru/SETUP.md).
Инструкция для мобильных пользователей Android доступна в [docs/ru/CLIENT_ANDROID.md](docs/ru/CLIENT_ANDROID.md).
