# Deployment and Setup Guide for WhitelistBypass Wrapper

## Method 1. One-Liner Installation via curl (Recommended)

**For public repository:**
```bash
curl -fsSL https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo bash -s -- --build-creators
```

**For private repository (with token):**
```bash
curl -fsSL -H "Authorization: token $GITHUB_TOKEN" https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo GITHUB_TOKEN=$GITHUB_TOKEN bash -s -- --build-creators
```

---

## Method 2. Installation from a Cloned Repository

```bash
git clone https://github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git
cd nadamu-whitelist-bypass-wrapper

sudo ./install.sh --build-creators
```

The installer automatically:
- Creates the isolated system user `whitelist-bypass`
- Prepares directory structures with strict permissions
- Installs the CLI utility into `/usr/local/bin/whitelist-bypass`
- Registers and reloads the systemd service template `whitelist-bypass@.service`
- Configures passwordless sudoers rules
- Installs shell completions for Bash and Zsh
- Installs the man page documentation (`man whitelist-bypass`)
- Compiles latest creator binaries from upstream master with slot-kill fixes

To **update** the project in the future:
```bash
git pull
sudo ./install.sh
```

---

## Method 3. Manual Step-by-Step Installation

### 1. System and User Preparation

Run as `root`:

```bash
# 1. Install base utilities
apt update && apt install -y curl jq sudo procps qrencode

# 2. Create isolated system user
useradd -r -s /usr/sbin/nologin -d /opt/whitelist-bypass -m whitelist-bypass

# 3. Create directory tree
mkdir -p /opt/whitelist-bypass/bin
mkdir -p /etc/whitelist-bypass/users

# 4. Set ownership and permissions
chown -R whitelist-bypass:whitelist-bypass /opt/whitelist-bypass /etc/whitelist-bypass
chmod 700 /etc/whitelist-bypass/users
```

---

### 2. Core Binaries (Creators)

Download precompiled creator binaries from [kulikov0/whitelist-bypass releases](https://github.com/kulikov0/whitelist-bypass/releases) into `/opt/whitelist-bypass/bin/`:

- `headless-telemost-creator` (Yandex.Telemost)
- `headless-vk-creator` (VK Calls)
- `headless-wbstream-creator` (WB Stream, optional)
- `headless-dion-creator` (DION, optional)

Or build them from source:
```bash
./scripts/build-latest-creators.sh /opt/whitelist-bypass/bin
chown -R whitelist-bypass:whitelist-bypass /opt/whitelist-bypass/bin
chmod +x /opt/whitelist-bypass/bin/headless-*-creator
```

---

### 3. CLI Orchestrator, systemd Unit, and Documentation

```bash
# 1. Install CLI orchestrator
cp bin/whitelist-bypass /usr/local/bin/whitelist-bypass
chmod +x /usr/local/bin/whitelist-bypass

# 2. Install Bash completion
cp completions/bash/whitelist-bypass /etc/bash_completion.d/whitelist-bypass

# 3. Install Zsh completion
mkdir -p /usr/local/share/zsh/site-functions
cp completions/zsh/_whitelist-bypass /usr/local/share/zsh/site-functions/_whitelist-bypass

# 4. Install man page
mkdir -p /usr/share/man/man1
cp man/whitelist-bypass.1 /usr/share/man/man1/whitelist-bypass.1
mandb 2>/dev/null || true

# 5. Install systemd template unit
cp systemd/whitelist-bypass@.service /etc/systemd/system/whitelist-bypass@.service
systemctl daemon-reload

# 6. Install sudoers configuration
cp sudoers/whitelist-bypass /etc/sudoers.d/whitelist-bypass
chmod 0440 /etc/sudoers.d/whitelist-bypass
```

---

## 4. Provisioning a User

Each user is isolated in their own directory:
`/etc/whitelist-bypass/users/<username>/`

### Step 4.1. Create User Directory

```bash
sudo -u whitelist-bypass mkdir -p /etc/whitelist-bypass/users/danya
chmod 700 /etc/whitelist-bypass/users/danya
```

### Step 4.2. Export Session Cookies

1. Log into your account on `telemost.yandex.ru` or `vk.com` in your desktop browser.
2. Export cookies in JSON format using a browser extension (e.g. *Cookie-Editor*).
3. Save the JSON file on the server:
   - For Telemost: `/etc/whitelist-bypass/users/danya/cookies-telemost.json` (or `cookies.json`)
   - For VK Calls: `/etc/whitelist-bypass/users/danya/cookies-vk.json`
4. Set strict file permissions:
   ```bash
   chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/cookies-*.json
   chmod 600 /etc/whitelist-bypass/users/danya/cookies-*.json
   ```

### Step 4.3. User Configuration (`user.conf`)

Create `/etc/whitelist-bypass/users/danya/user.conf`:

```ini
PROVIDER=telemost
RESOURCES=default
UPSTREAM_SOCKS=
DEBUG=false
```

Set permissions:
```bash
chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/user.conf
chmod 600 /etc/whitelist-bypass/users/danya/user.conf
```

---

## 5. First Run and Room Generation

Generate the initial conference room and start the tunnel:

```bash
whitelist-bypass rotate danya --qr
```

The orchestrator will:
1. Start the systemd service `whitelist-bypass@danya`.
2. Wait for the SFU media server to provision the conference room.
3. Persist the link into `/etc/whitelist-bypass/users/danya/room.env`.
4. Render an ANSI UTF-8 QR code and print the textual link in the terminal.

List all configured users:
```bash
whitelist-bypass list
```

Retrieve current link at any time:
```bash
whitelist-bypass get-link danya
```

Display terminal QR code for mobile connection:
```bash
whitelist-bypass qr danya
```

---

## 6. Switching Platforms/Providers (e.g., Telemost $\leftrightarrow$ VK Calls)

The orchestrator supports concurrent cookie storage in the user directory:
- `cookies-telemost.json` (or `cookies-yandex.json`)
- `cookies-vk.json`
- `cookies-wbstream.json`
- `cookies-dion.json`

### Switch in a single command:

1. Save VK cookies to the user folder:
   ```bash
   cat << 'EOF' > /etc/whitelist-bypass/users/danya/cookies-vk.json
   [ ... exported vk.com JSON cookies ... ]
   EOF
   chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/cookies-vk.json
   chmod 600 /etc/whitelist-bypass/users/danya/cookies-vk.json
   ```

2. Run the provider switch command:
   ```bash
   whitelist-bypass set-provider danya vk --rotate
   ```
   The `--rotate` flag stops the previous daemon, updates `PROVIDER=vk` in `user.conf`, creates a new VK Calls room, and displays the QR code immediately.
