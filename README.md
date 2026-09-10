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

## Быстрый старт

Подробное руководство по ручной установке описано в [docs/SETUP.md](docs/SETUP.md).

Базовые команды управления:
```bash
# Показать список пользователей и их статус
whitelist-bypass list

# Создать новую чистую комнату для пользователя
whitelist-bypass rotate <username>

# Получить текущую ссылку пользователя
whitelist-bypass get-link <username>

# Управление службой
whitelist-bypass start <username>
whitelist-bypass stop <username>
whitelist-bypass status <username>
```

Инструкция для мобильных пользователей Android доступна в [docs/CLIENT_ANDROID.md](docs/CLIENT_ANDROID.md).
