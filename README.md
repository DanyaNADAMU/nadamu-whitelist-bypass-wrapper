# nadamu-whitelist-bypass-wrapper

**English** | [Русская версия](README.ru.md)

Multi-account server-side wrapper and lifecycle orchestrator for [kulikov0/whitelist-bypass](https://github.com/kulikov0/whitelist-bypass).

Encapsulates L4 network traffic (TCP/UDP) over WebRTC sessions (such as Yandex.Telemost, VK Calls, WB Stream, or DION) through Russian cloud media servers to bypass carrier-grade whitelisting and network censorship.

---

## Key Features

- **Strict 1:1:1 Isolation:** 1 user = 1 service account (cookies) = 1 active room = 1 isolated headless creator daemon.
- **Local API & Systemd Core:** Background daemon `whitelist-bypass-core.service` exposing REST API over Unix Domain Socket (`/run/whitelist-bypass/core.sock`).
- **Unified Command System:** Identical command registry, syntax, and structured `--json` output across CLI, Telegram/VK bots, and web interfaces.
- **Multi-Provider Support:** Yandex.Telemost, VK Calls, WB Stream, DION unified under a single interface.
- **Instant Provider Switching:** CLI command `whitelist-bypass provider <user> <provider> [--rotate]` for seamless platform switching.
- **In-Terminal QR Codes:** Command `whitelist-bypass qr <user>` with automatic ANSI half-block formatting and dark theme contrast preservation.
- **Deterministic Room Rotation:** Native `--write-file` synchronization eliminates fragile race conditions and arbitrary sleep intervals.
- **Hardened systemd Isolation:** Templated `whitelist-bypass@<username>.service` units enforced with `ProtectSystem=strict` and `NoNewPrivileges=true`.
- **Zero-Downtime Fallback:** CLI functions with zero disruption whether the Core daemon is running or temporarily offline (direct in-process execution).

---

## Repository Structure

```text
.
├── bin/
│   └── whitelist-bypass             # Universal CLI entrypoint
├── core/                            # Python Core engine and local API
│   ├── app.py                       # FastAPI REST API & UDS daemon
│   ├── client.py                    # Client library with offline fallback
│   ├── commands.py                  # Unified command registry
│   ├── config.py                    # System configuration & path resolution
│   ├── models.py                    # Data classes and domain models
│   └── services/                    # Core business logic services
│       ├── qr_service.py            # ANSI UTF-8 & Base64 QR generator
│       ├── tunnel_service.py        # Systemd supervisor & room rotator
│       └── user_service.py          # User configurations & cookie resolution
├── systemd/
│   ├── whitelist-bypass-core.service# Core daemon systemd service
│   └── whitelist-bypass@.service    # Hardened user tunnel service template
├── sudoers/
│   └── whitelist-bypass             # Sudoers privilege escalation rules
├── completions/
│   ├── bash/whitelist-bypass        # Native Bash completion script
│   └── zsh/_whitelist-bypass        # Native Zsh completion definition
├── man/
│   └── whitelist-bypass.1           # Unix man page (man whitelist-bypass)
├── examples/
│   ├── user.conf.example            # Example user configuration file
│   └── room.env.example             # Example persisted room environment file
├── docs/
│   ├── en/                          # Documentation in English
│   │   ├── SETUP.md                 # Step-by-step setup and operations guide
│   │   └── CLIENT_ANDROID.md        # Android Joiner client configuration guide
│   └── ru/                          # Documentation in Russian
│       ├── SETUP.md                 # Пошаговая инструкция по установке
│       └── CLIENT_ANDROID.md        # Настройка клиента Android
├── requirements.txt                 # Core daemon Python dependencies
├── install.sh                       # Idempotent installer and updater
├── uninstall.sh                     # Safe uninstaller
└── PLAN.md                          # Architectural roadmap and milestones (in Russian)
```

---

## Quick Installation via curl

**When repository is public:**
```bash
curl -fsSL https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo bash -s -- --build-creators
```

**While repository is private:**
```bash
# Pass your GitHub Personal Access Token (PAT):
curl -fsSL -H "Authorization: token $GITHUB_TOKEN" https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo GITHUB_TOKEN=$GITHUB_TOKEN bash -s -- --build-creators
```

---

## Local Installation and Updates

```bash
git clone https://github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git
cd nadamu-whitelist-bypass-wrapper

sudo ./install.sh --build-creators
```

The installer:
- Provisions the isolated system user `whitelist-bypass`
- Deploys the CLI binary to `/usr/local/bin/whitelist-bypass`
- Installs the systemd unit `whitelist-bypass@.service`
- Configures passwordless sudoers rules
- Configures Bash/Zsh shell completions and man page
- Verifies `qrencode` availability for terminal QR codes
- Compiles latest creator binaries from upstream master

To **update** an existing deployment:
```bash
git pull
sudo ./install.sh
```

To **uninstall**:
```bash
sudo ./uninstall.sh          # Preserves user data and cookies
sudo ./uninstall.sh --purge  # Complete cleanup including user configs
```

---

## Basic CLI Commands

```bash
# Display all configured users and their tunnel statuses
whitelist-bypass list

# Provision a fresh conference room (with terminal QR code)
whitelist-bypass rotate <username> --qr

# Retrieve current room URL
whitelist-bypass get-link <username>
whitelist-bypass get-link <username> --qr

# Display instant QR code for mobile client connection
whitelist-bypass qr <username>

# Switch provider (telemost, vk, wbstream, dion) and rotate room
whitelist-bypass set-provider <username> vk --rotate

# Service lifecycle control
whitelist-bypass start <username>
whitelist-bypass stop <username>
whitelist-bypass status <username>
```

For complete manual setup details, see [docs/en/SETUP.md](docs/en/SETUP.md).
For mobile client instructions, see [docs/en/CLIENT_ANDROID.md](docs/en/CLIENT_ANDROID.md).
