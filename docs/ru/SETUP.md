# Руководство по развертыванию WhitelistBypass Wrapper

## Способ 1. Установка в одну команду через curl (Рекомендуется)

**Для публичного репозитория:**
```bash
curl -fsSL https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo bash -s -- --build-creators
```

**Для приватного репозитория (с токеном):**
```bash
curl -fsSL -H "Authorization: token $GITHUB_TOKEN" https://raw.githubusercontent.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper/main/install.sh | sudo GITHUB_TOKEN=$GITHUB_TOKEN bash -s -- --build-creators
```

---

## Способ 2. Установка из локально склонированного репозитория

```bash
git clone https://github.com/DanyaNADAMU/nadamu-whitelist-bypass-wrapper.git
cd nadamu-whitelist-bypass-wrapper

sudo ./install.sh --build-creators
```

Инсталлятор сам создаст пользователя, каталоги, скопирует все бинарники, настроит службу systemd, sudoers, автодополнение Bash и man-страницу.

Для **обновления** проекта в будущем:
```bash
git pull
sudo ./install.sh
```

---

## Способ 3. Ручная пошаговая установка


## 1. Подготовка системы и пользователя

Выполняется под пользователем `root`:

```bash
# 1. Установка базовых системных утилит
apt update && apt install -y curl jq sudo procps qrencode

# 2. Создание системного пользователя для изоляции
useradd -r -s /usr/sbin/nologin -d /opt/whitelist-bypass -m whitelist-bypass

# 3. Создание структуры каталогов
mkdir -p /opt/whitelist-bypass/bin
mkdir -p /etc/whitelist-bypass/users

# 4. Назначение владельцев и прав
chown -R whitelist-bypass:whitelist-bypass /opt/whitelist-bypass /etc/whitelist-bypass
chmod 700 /etc/whitelist-bypass/users
```

---

## 2. Установка бинарников ядра (Creators)

Скачайте актуальные скомпилированные бинарники из релизов [kulikov0/whitelist-bypass](https://github.com/kulikov0/whitelist-bypass/releases) в `/opt/whitelist-bypass/bin/`:

- `headless-telemost-creator` (Яндекс.Телемост)
- `headless-vk-creator` (VK Звонки)
- `headless-wbstream-creator` (WB Stream, опционально)
- `headless-dion-creator` (DION, опционально)

```bash
# Назначение прав на запуск
chown -R whitelist-bypass:whitelist-bypass /opt/whitelist-bypass/bin
chmod +x /opt/whitelist-bypass/bin/headless-*-creator
```

---

## 3. Установка CLI-оркестратора, службы systemd и документации

Скопируйте файлы из этого репозитория:

```bash
# 1. Установка CLI оркестратора
cp bin/whitelist-bypass /usr/local/bin/whitelist-bypass
chmod +x /usr/local/bin/whitelist-bypass

# 2. Установка автодополнения (Tab-completion) в Bash
cp completions/whitelist-bypass /etc/bash_completion.d/whitelist-bypass

# 3. Установка страницы руководства (man)
mkdir -p /usr/share/man/man1
cp man/whitelist-bypass.1 /usr/share/man/man1/whitelist-bypass.1
mandb 2>/dev/null || true

# 4. Установка шаблона службы systemd
cp systemd/whitelist-bypass@.service /etc/systemd/system/whitelist-bypass@.service
systemctl daemon-reload

# 5. Настройка прав sudoers для непривилегированного пользователя
cp sudoers/whitelist-bypass /etc/sudoers.d/whitelist-bypass
chmod 0440 /etc/sudoers.d/whitelist-bypass
```

---

## 4. Добавление нового пользователя

Каждый пользователь изолирован в собственной директории:
`/etc/whitelist-bypass/users/<имя_пользователя>/`

### Шаг 4.1. Создание папки пользователя

```bash
sudo -u whitelist-bypass mkdir -p /etc/whitelist-bypass/users/danya
chmod 700 /etc/whitelist-bypass/users/danya
```

### Шаг 4.2. Экспорт Cookies

1. Пользователь заходит в браузере на `telemost.yandex.ru` (или `vk.com`) под своим аккаунтом.
2. С помощью расширения (например, *Cookie-Editor*) экспортирует cookies в формате JSON.
3. Сохраняет файл на сервере:
   - Для Телемоста: `/etc/whitelist-bypass/users/danya/cookies.json` (или `cookies-telemost.json`)
   - Для VK: `/etc/whitelist-bypass/users/danya/cookies.json` (или `cookies-vk.json`)
4. Устанавливаются строгие права:
   ```bash
   chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/cookies.json
   chmod 600 /etc/whitelist-bypass/users/danya/cookies.json
   ```

### Шаг 4.3. Настройка конфигурации (`user.conf`)

Создайте `/etc/whitelist-bypass/users/danya/user.conf`:

```ini
PROVIDER=telemost
RESOURCES=default
UPSTREAM_SOCKS=
DEBUG=false
```

Права на файл:
```bash
chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/user.conf
chmod 600 /etc/whitelist-bypass/users/danya/user.conf
```

---

## 5. Первый запуск и генерация ссылки

Для первичной генерации комнаты и старта туннеля выполните:

```bash
sudo -u whitelist-bypass /usr/local/bin/whitelist-bypass rotate danya
```

Оркестратор:
1. Запустит службу `whitelist-bypass@danya`.
2. Дождется генерации новой чистой комнаты на стороне медиа-сервера.
3. Сохранит ссылку в `/etc/whitelist-bypass/users/danya/room.env`.
4. Выведет ссылку в терминал.

Проверка статуса всех пользователей:
```bash
whitelist-bypass list
```

Получение текущей ссылки в любое время:
```bash
whitelist-bypass get-link danya
```

Отображение QR-кода ссылки для быстрого подключения мобильного клиента:
```bash
whitelist-bypass qr danya
# Или с флагом --qr при получении ссылки или ротации:
whitelist-bypass get-link danya --qr
whitelist-bypass rotate danya --qr
```

---

## 6. Смена платформы/провайдера (например, с Telemost на VK)

Оркестратор поддерживает одновременное хранение cookies для разных сервисов в каталоге пользователя:
- `cookies-telemost.json` (или `cookies-yandex.json`)
- `cookies-vk.json`
- `cookies-wbstream.json`
- `cookies-dion.json`

### Быстрая смена в одну команду:

1. Сохраните cookies ВКонтакте в файл пользователя:
   ```bash
   # Экспортируйте cookies с сайта vk.com через Cookie-Editor в JSON
   cat << 'EOF' > /etc/whitelist-bypass/users/danya/cookies-vk.json
   [ ... cookies json ... ]
   EOF
   chown whitelist-bypass:whitelist-bypass /etc/whitelist-bypass/users/danya/cookies-vk.json
   chmod 600 /etc/whitelist-bypass/users/danya/cookies-vk.json
   ```

2. Выполните команду смены провайдера:
   ```bash
   whitelist-bypass set-provider danya vk --rotate
   ```
   Флаг `--rotate` сразу остановит службу Телемоста, переключит `PROVIDER=vk` в `user.conf`, создаст новую комнату VK Звонков и выведет в терминал готовый QR-код для подключения.

