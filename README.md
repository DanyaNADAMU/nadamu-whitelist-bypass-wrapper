# nadamu-whitelist-bypass-wrapper

Мульти-аккаунтная серверная обертка и диспетчер для [kulikov0/whitelist-bypass](https://github.com/kulikov0/whitelist-bypass).

Решает задачу туннелирования интернет-трафика (L4-over-WebRTC) через медиа-серверы российских сервисов (Яндекс.Телемост, VK Звонки, WB Stream, DION) в условиях строгих белых списков операторов связи.

---

## Ключевые возможности

- **Строгая изоляция 1:1:1:** 1 пользователь = 1 сервисный аккаунт (cookies) = 1 активная комната = 1 изолированный headless-creator.
- **Поддержка всех провайдеров:** Яндекс.Телемост, VK Звонки, WB Stream, DION через единый интерфейс.
- **Надежная ротация комнат:** автоматическая генерация и фиксация ссылок через флаг ядра `--write-file` без таймаутных костылей (`sleep`).
- **Управление через systemd:** шаблонизированный изолированный сервис `whitelist-bypass@<username>.service` с жесткими ограничениями (`ProtectSystem=strict`, `NoNewPrivileges=true`).
- **Удобный CLI-оркестратор:** утилита `whitelist-bypass` для управления жизненным циклом комнат и мониторинга пользователей.
- **Интерфейсы управления (в разработке):** модульные боты для VK и Telegram.

---

## Структура репозитория

```text
.
├── bin/
│   └── whitelist-bypass             # Главный CLI-оркестратор
├── systemd/
│   └── whitelist-bypass@.service    # Шаблон службы systemd для пользователей
├── sudoers/
│   └── whitelist-bypass             # Правило sudoers для служебного пользователя
├── examples/
│   ├── user.conf.example            # Пример файла конфигурации пользователя
│   └── room.env.example             # Пример файла сохраненной ссылки
├── docs/
│   ├── SETUP.md                     # Пошаговая инструкция по ручному развертыванию
│   └── CLIENT_ANDROID.md            # Инструкция по настройке Android-клиента
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
- Подключает автодополнение Bash и man-страницу
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


Базовые команды управления:
```bash
# Показать список пользователей и их статус
whitelist-bypass list

# Создать новую чистую комнату для пользователя (с выводом QR-кода при необходимости)
whitelist-bypass rotate <username>
whitelist-bypass rotate <username> --qr

# Получить текущую ссылку пользователя
whitelist-bypass get-link <username>
whitelist-bypass get-link <username> --qr

# Быстрый вывод QR-кода ссылки прямо в терминале для мобильного клиента
whitelist-bypass qr <username>

# Управление службой
whitelist-bypass start <username>
whitelist-bypass stop <username>
whitelist-bypass status <username>
```

Инструкция для мобильных пользователей Android доступна в [docs/CLIENT_ANDROID.md](docs/CLIENT_ANDROID.md).
