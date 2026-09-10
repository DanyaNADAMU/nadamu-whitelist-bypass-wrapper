# WhitelistBypass Wrapper: Архитектура и дорожная карта проекта

## 1. Введение и концепция

Проект решает задачу обеспечения стабильного выхода в интернет в условиях блокировок по «белым спискам» (когда операторы связи блокируют доступ ко всем внешним ресурсам, оставляя доступными только сервисы из белого списка: VK, Госуслуги, Яндекс и др.).

### Принцип работы
Сетевой L4-трафик (TCP/UDP) перехватывается на клиентском устройстве (Android), маскируется под полезную нагрузку WebRTC (видеопоток кодека VP8 для Яндекс.Телемост или WebRTC SCTP DataChannels для VK Звонков) и передается через официальные публичные медиа-серверы (SFU). На выходной ноде (VPS) headless-демон Creator распаковывает полезную нагрузку и отправляет сетевые запросы в свободную сеть (напрямую в РФ или через upstream SOCKS5 прокси).

---

## 2. Архитектурные правила и принципы

1. **Строгое правило 1:1:1 (1 Пользователь = 1 Аккаунт = 1 Активная комната):**
   - Платформы видеоконференций не терпят многопользовательских коллизий внутри одной WebRTC-сессии.
   - У каждого пользователя на сервере выделен свой изолированный каталог, конфигурация (`user.conf`), сессионные cookies (`cookies-$provider.json`) и отдельный инстанс службы `whitelist-bypass@<username>.service`.
2. **Полупостоянные ссылки (Ротация по требованию):**
   - Ссылка на комнату сохраняется в файле `room.env` (`CALL_LINK=...`) и не меняется при обычных перезапусках демона.
   - Новая чистая комната создается только по явной команде пользователя (`rotate`), когда старая сессия деградировала или завершилась.
3. **Надежная генерация ссылок (Native `--write-file`):**
   - Никаких эвристических ожиданий (`sleep`) или грубых убийств процессов.
   - Бинарник ядра при запуске сам атомарно записывает актуальный URL в файл `--write-file current_link`, откуда ссылка считывается и верифицируется сервисом.
4. **Валидация сессионных cookies:**
   - Перед стартом туннеля проверяется размер файла кук (>15 байт). Пустые заглушки или битые файлы немедленно отклоняются с понятной диагностической ошибкой.
   - Приоритет поиска: `cookies-$provider.json` -> `cookies-yandex.json` (для telemost) -> `cookies.json`.
5. **Единое системное ядро (Systemd Core Daemon + UDS):**
   - Фоновый сервис `whitelist-bypass-core.service` управляет состоянием пользователей, ротацией, блокировками и предоставляет локальный REST API.
   - Транспорт по умолчанию — Unix Domain Socket (`/run/whitelist-bypass/core.sock`), с опциональным локальным HTTP-портом (`127.0.0.1:8080`).
   - Бесшовный fallback: CLI-утилита умеет работать как через ядро, так и напрямую (in-process), если демон ядра временно остановлен.
6. **Единый реестр команд (Unified Command Registry):**
   - Все интерфейсы (CLI, Telegram-бот, VK-бот, Next.js Web UI, REST API) используют одинаковые имена команд, параметры, семантику и структуру JSON-ответов.
7. **Защита от ловушки Android Private DNS (DoT):**
   - Android по умолчанию отправляет запросы DNS-over-TLS на порт 853 оператора связи (например, МТС `213.87.x.x:853`). В условиях белых списков эти запросы падают по таймауту, из-за чего ОС считает интернет отсутствующим.
   - Требование к клиентам: Private DNS должен быть выключен в системе, а в приложении Joiner жестко задан публичный DNS (`77.88.8.8` или `8.8.8.8`).

---

## 3. Архитектура ядра и интерфейсов

```text
                        ┌──────────────────────────────────────────────┐
                        │              Клиентские интерфейсы           │
                        │                                              │
                        │   CLI:      whitelist-bypass <command>       │
                        │   Telegram: /link, /rotate, /status, /help   │
                        │   VK Bot:   /link, /rotate, /status, /help   │
                        │   Next.js:  Веб-панель (Fetch / UDS HTTP)    │
                        └──────────────────────┬───────────────────────┘
                                               │
                       JSON-RPC / REST через Unix Socket (/run/whitelist-bypass/core.sock)
                                (или fallback in-process для CLI)
                                               │
                        ┌──────────────────────▼───────────────────────┐
                        │      whitelist-bypass-core.service           │
                        │   (Python Daemon: FastAPI + Uvicorn)         │
                        │                                              │
                        │  • Unified Command Registry (core.commands)  │
                        │  • User Management Service (core.services)   │
                        │  • Tunnel & Process Supervisor               │
                        │  • Per-User Async Locks (asyncio.Lock)       │
                        │  • QR Generator (ANSI UTF-8, PNG Base64)     │
                        └──────────────────────┬───────────────────────┘
                                               │
                        ┌──────────────────────┴───────────────────────┐
                        │                                              │
               systemctl control                              os.exec / FS
                        │                                              │
       ┌────────────────▼───────────────┐             ┌────────────────▼───────────────┐
       │ whitelist-bypass@<user>.service│             │    /etc/whitelist-bypass/      │
       │   • headless-vk-creator        │             │    ├── users/<user>/           │
       │   • headless-telemost-creator  │             │    │   ├── user.conf           │
       │   • headless-wbstream-creator  │             │    │   ├── cookies-vk.json     │
       │   • headless-dion-creator      │             │    │   ├── room.env            │
       └────────────────────────────────┘             │    │   └── current_link        │
                                                      │    └── core.env                │
                                                      └────────────────────────────────┘
```

### Разрешение контекста пользователя (Identity Resolution)
- **В консоли (CLI):** Пользователь всегда явно указывает целевого пользователя: `whitelist-bypass link <user>` или `whitelist-bypass rotate <user>`.
- **В ботах (Telegram / VK):** Бот автоматически определяет пользователя по `TELEGRAM_ID` или `VK_ID`, прописанному в `/etc/whitelist-bypass/users/<username>/user.conf`.
- **Для администраторов в ботах:** Если ID пользователя входит в список администраторов, он может передавать имя пользователя точно так же, как в CLI: `/link danya`, `/rotate friend`.

---

## 4. Спецификация унифицированных команд

Все команды имеют единое имя, короткие алиасы и принимают флаг `--json` для программной интеграции:

| Команда | Алиас | Аргументы | Описание |
| :--- | :--- | :--- | :--- |
| `link` | `get-link` | `<user>` `[--qr]` | Показать активную ссылку на конференцию и статус сервиса |
| `qr` | — | `<user>` | Вывести QR-код (терминальный ANSI UTF-8 или графический Base64) |
| `rotate` | — | `<user>` `[--qr]` | Пересоздать комнату и сохранить новую ссылку |
| `provider` | `set-provider` | `<user> <provider>` `[--rotate]` | Сменить провайдера (`telemost`, `vk`, `wbstream`, `dion`) |
| `status` | — | `<user>` | Детальный статус туннеля, конфигурации и валидности cookies |
| `start` | — | `<user>` | Запустить туннель пользователя |
| `stop` | — | `<user>` | Остановить туннель пользователя |
| `restart` | — | `<user>` | Перезапустить туннель пользователя |
| `is-active` | — | `<user>` | Проверка активности сервиса (`active` / `inactive`) |
| `list` | — | — | Список всех пользователей, провайдеров и статусов |
| `run` | — | `<user>` | Внутренний раннер (вызывается из `whitelist-bypass@<user>.service`) |
| `help` | `-h`, `--help` | — | Справка по командам |

---

## 5. Иерархия файлов и директорий

```text
/etc/whitelist-bypass/
├── core.env                        # [0600] Настройки ядра (сокет, HTTP хост/порт)
└── users/
    ├── danya/
    │   ├── user.conf               # [0600] PROVIDER=vk, TELEGRAM_ID=..., VK_ID=...
    │   ├── cookies-vk.json         # [0600] Сессионные куки VK
    │   ├── cookies-telemost.json   # [0600] Сессионные куки Яндекс
    │   ├── room.env                # [0600] CALL_LINK="https://calls.vk.ru/join/..."
    │   └── current_link            # [0644] Файл текущей активной ссылки
    └── friend/
        ├── user.conf               # PROVIDER=telemost
        └── cookies.json

/run/whitelist-bypass/
└── core.sock                       # [0660 whitelist-bypass:whitelist-bypass] UDS API сокет

/opt/whitelist-bypass/
├── bin/
│   ├── headless-telemost-creator   # [0755] Бинарники ядра (Go)
│   └── headless-vk-creator         # [0755]
├── core/                           # Python-пакет ядра
│   ├── app.py                      # FastAPI REST API приложение
│   ├── client.py                   # Клиент UDS / HTTP / fallback
│   ├── commands.py                 # Единый реестр команд
│   ├── config.py                   # Конфигурация и пути
│   ├── models.py                   # Модели данных (Pydantic / Dataclasses)
│   └── services/                   # Сервисный слой
│       ├── user_service.py         # Управление конфигами, куками и пользователями
│       ├── tunnel_service.py       # systemd, ротация, блокировки, exec creator
│       └── qr_service.py           # Рендеринг QR-кодов
└── venv/                           # Изолированное виртуальное окружение Python

/usr/local/bin/
└── whitelist-bypass                # [0755] Единая CLI-утилита (вызывает core.cli)

/etc/systemd/system/
├── whitelist-bypass-core.service   # Сервис демона ядра API
└── whitelist-bypass@.service       # Шаблон сервиса для туннелей пользователей
```

---

## 6. Дорожная карта разработки

### Этап 1. Системный слой оркестрации (Завершено)
- [x] Разработка начального CLI-оркестратора `bin/whitelist-bypass`.
- [x] Реализация команд: `run`, `get-link`, `rotate`, `list`, `start`, `stop`, `restart`, `status`.
- [x] Мультипровайдерность (`telemost`, `vk`, `wbstream`, `dion`) и команда `set-provider`.
- [x] Терминальные QR-коды (`qrencode -t ANSIUTF8 -m 2`).
- [x] Приоритет cookies (`cookies-$provider.json`) и строгая валидация размера (>15 байт).
- [x] Шаблон службы systemd `whitelist-bypass@.service` с изоляцией.
- [x] Настройка прав sudoers `sudoers/whitelist-bypass`.
- [x] Полная интернационализация кода и локализация документации (`docs/en`, `docs/ru`, `README.md`, `README.ru.md`).

### Этап 2. Systemd-ядро и унифицированный CLI (Завершено)
- [x] Проектирование архитектуры демона ядра с локальным API.
- [x] Разработка Python-пакета `core/`:
  - [x] `core/config.py`: загрузка параметров и путей.
  - [x] `core/models.py`: типизированные структуры пользователей, сервисов и статусов.
  - [x] `core/commands.py`: единый реестр команд, параметров, алиасов и валидаторов.
  - [x] `core/services/user_service.py`: парсинг `user.conf`, приоритет и валидация cookies, привязка `TELEGRAM_ID` / `VK_ID`.
  - [x] `core/services/tunnel_service.py`: управление `systemctl`, безопасная ротация через `--write-file`, per-user `asyncio.Lock()`, direct `os.execvp` для `run`.
  - [x] `core/services/qr_service.py`: генерация ANSI UTF-8 и Base64/PNG QR-кодов.
  - [x] `core/client.py`: клиент поверх Unix Domain Socket (`/run/whitelist-bypass/core.sock`) с авто-фоллбэком на прямой вызов сервисов.
  - [x] `core/app.py`: FastAPI сервис (UDS + опциональный HTTP).
  - [x] `core/cli.py`: унифицированный CLI-интерфейс с поддержкой цветного терминального вывода и `--json`.
- [x] Служба `systemd/whitelist-bypass-core.service`.
- [x] Обновление `bin/whitelist-bypass` для вызова `core.cli`.
- [x] Обновление `install.sh` (развертывание venv, регистрация сервиса ядра).
- [x] Тестирование и верификация на сервере (запущено и протестировано на `berg`).

### Этап 3. Боты (В процессе)
- [x] Telegram Бот (`bot/telegram/`):
  - [x] Aiogram 3 с LongPolling.
  - [x] Авторизация и контекстное разрешение пользователя по `TELEGRAM_ID` из `user.conf`.
  - [x] Панель администратора (`ADMIN_IDS`) с командами `/list`, `/link <user>`, `/rotate <user>`, `/status <user>`.
  - [x] Команды: `/link`, `/qr`, `/rotate`, `/provider`, `/status`, `/help`.
  - [x] Inline-клавиатуры для моментальной ротации и выбора провайдера в один клик.
  - [x] Отправка QR-кода готовой картинкой (`send_photo`).
  - [x] Служба systemd `whitelist-bypass-telegram-bot.service` с конфигурацией в `/etc/whitelist-bypass/telegram-bot.env`.
- [x] VK Бот (`bot/vk/`):
  - [x] VK Bots LongPoll API (v5.199) на aiohttp без избыточных зависимостей.
  - [x] Разрешение пользователя по `VK_ID` из `user.conf`.
  - [x] Панель администратора (`VK_ADMIN_IDS`) с расширенными командами управления.
  - [x] Команды: `/link`, `/qr`, `/rotate`, `/provider`, `/status`, `/restart`, `/start_service`, `/stop_service`, `/list`, `/help`.
  - [x] Inline-клавиатуры для моментальной ротации и выбора провайдера.
  - [x] Загрузка QR-кода на сервера VK через multipart upload (`photos.saveMessagesPhoto`).
  - [x] Служба systemd `whitelist-bypass-vk-bot.service` с конфигурацией в `/etc/whitelist-bypass/vk-bot.env`.

### Этап 4. Веб-интерфейс (Next.js Dashboard)
- [ ] Панель управления на Next.js (App Router):
  - Подключение к ядру через локальный UDS (`/run/whitelist-bypass/core.sock`) или HTTP (`127.0.0.1:8080`).
  - Управление пользователями, просмотр статусов и логов.
  - Ротация и сменяемость провайдеров в UI.
  - Модальное окно с QR-кодом для быстрого сканирования смартфоном.

### Этап 5. Контейнеризация (Docker)
- [ ] Dockerfile и Docker Compose:
  - Контейнер для ядра API и ботов / веб-панели.
  - Монтирование `/run/whitelist-bypass` и `/etc/whitelist-bypass`.
  - Возможность гибридного запуска (нативные creators на хосте, панель и ядро в контейнере).

### Этап 6. Мониторинг и самовосстановление
- [ ] Команда расширенного аудита `whitelist-bypass healthcheck <username>` (проверка валидности cookies, доступности SFU).
- [ ] Периодический фоновый монитор зависших комнат.

