# Feature Implementation and Testing Matrix

This document tracks the current implementation and live testing status of **Iris (WhitelistBypass Wrapper)** components across environments.

**Live Target Server:** `berg` (Debian GNU/Linux 13 / Trixie x86_64, Linux 6.12)  
**Active Test User:** `danya`  
**Active Media Provider:** `VK Calls`

---

## 1. System Layer and Services (Systemd & Creators)

| Component / Feature | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| Service template `whitelist-bypass@.service` | ✅ Completed | ✅ Tested | Runs under `whitelist-bypass` with `NoNewPrivileges=true` |
| **VK Calls** provider support | ✅ Completed | ✅ Tested | `headless-vk-creator` generates valid links and holds active sessions |
| **Yandex.Telemost** provider support | ✅ Completed | ✅ Tested | `headless-telemost-creator` verified during Phase 1 |
| **WB Stream** provider support | ✅ Completed | ⚠️ Awaiting cookies | Binary compiled and integrated; requires real WB cookies |
| **DION** provider support | ✅ Completed | ⚠️ Awaiting cookies | Binary compiled and integrated; requires real DION cookies |
| Cookie validation (>15 bytes) | ✅ Completed | ✅ Tested | Rejects zero-byte placeholders |
| Native `--write-file` synchronization | ✅ Completed | ✅ Tested | Atomic link output to `current_link` |

---

## 2. Core Engine and Local API (Core Daemon)

| Component / Feature | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| `whitelist-bypass-core.service` | ✅ Completed | ✅ Tested | Supervisor root unit managing systemctl |
| Unix Domain Socket (`/run/.../core.sock`)| ✅ Completed | ✅ Tested | Mode `0660 whitelist-bypass:whitelist-bypass` |
| Health check `/api/v1/health` | ✅ Completed | ✅ Tested | UDS socket liveness probe |
| Command gateway `/api/v1/commands/exec` | ✅ Completed | ✅ Tested | Unified execution registry gateway |
| User inspection `/api/v1/users` & detail | ✅ Completed | ✅ Tested | Returns user configuration and active links |
| Per-user locks (`asyncio.Lock`) | ✅ Completed | ✅ Tested | Eliminates race conditions during room rotation |

---

## 3. Command Line Interface (CLI)

| Command | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| `whitelist-bypass link <user>` | ✅ Completed | ✅ Tested | Retrieves active link and service status |
| `whitelist-bypass qr <user>` | ✅ Completed | ✅ Tested | Terminal UTF-8 ANSI QR via `qrencode` |
| `whitelist-bypass rotate <user>` | ✅ Completed | ✅ Tested | Re-provisions fresh room and updates `room.env` |
| `whitelist-bypass provider <user> <p>` | ✅ Completed | ✅ Tested | Platform switcher (verified switching to VK) |
| `whitelist-bypass status <user>` | ✅ Completed | ✅ Tested | Complete diagnostics: cookies, status, link |
| `whitelist-bypass list` | ✅ Completed | ✅ Tested | Overview table of all configured accounts |
| `whitelist-bypass start/stop/restart` | ✅ Completed | ✅ Tested | Lifecycle control via systemctl |
| `--json` flag | ✅ Completed | ✅ Tested | Position-independent structured JSON output |
| In-process offline fallback | ✅ Completed | ✅ Tested | Executes logic even if Core daemon is stopped |

---

## 4. Telegram Bot Dispatcher (@nadamu_iris_bot)

| Feature / Command | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :---: |
| `whitelist-bypass-telegram-bot` service | ✅ Completed | ✅ Tested | LongPolling via Aiogram 3 |
| Identity mapping by `TELEGRAM_ID` | ✅ Completed | ✅ Tested | Contextual resolution from `user.conf` |
| `/start` command | ✅ Completed | ✅ Tested | Live status queried via Core UDS API |
| `/link` command | ✅ Completed | ✅ Tested | Active link card with status badge |
| `/qr` command | ✅ Completed | ✅ Tested | Sends generated PNG directly to chat |
| `/rotate` command | ✅ Completed | ✅ Tested | Provisions fresh room with new QR code |
| `/provider` command | ✅ Completed | ✅ Tested | Inline keyboard platform switcher |
| `/status` command | ✅ Completed | ✅ Tested | Detailed diagnostics and cookie check |
| `/help` command | ✅ Completed | ✅ Tested | Role-aware command reference (User / Admin) |
| `/list` command (Admin) | ✅ Completed | ✅ Tested | Server user overview card |
| `[≡ Menu]` button & autocomplete | ✅ Completed | ✅ Tested | Multi-scope registration |
| `/restart`, `/start_service` commands | ✅ Completed | ⚠️ Awaiting live run | Non-blocking via run_in_executor |

---

## 5. VK Bot Dispatcher (VKontakte)

| Feature / Command | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| `whitelist-bypass-vk-bot` service | ✅ Completed | ⏳ Awaiting community token | VK Bots LongPoll API v5.199 |
| Identity mapping by `VK_ID` | ✅ Completed | ⏳ Untested | Resolution from `user.conf` |
| Commands `/link`, `/qr`, `/rotate` | ✅ Completed | ⏳ Untested | Consistent semantics with TG and CLI |
| Platform & rotation keyboards | ✅ Completed | ⏳ Untested | Native VK Inline Keyboards |
| QR code photo delivery | ✅ Completed | ⏳ Untested | Upload via `photos.saveMessagesPhoto` |
| Admin panel (`/list`, etc.) | ✅ Completed | ⏳ Untested | Protected by `VK_ADMIN_IDS` |

---

## 6. Web Dashboard (Next.js)

| Feature | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| Next.js App Router UI | ⏳ Planned | ⏳ Untested | Phase 4 |
| UDS socket connection | ⏳ Planned | ⏳ Untested | Node.js socketPath to `core.sock` |

---

## 7. Containerization (Docker)

| Feature | Development Status | Testing Status (`berg`) | Notes |
| :--- | :---: | :---: | :--- |
| Dockerfile & docker-compose.yml | ⏳ Planned | ⏳ Untested | Phase 5 |
