#!/usr/bin/env bash
#
# Build latest WhitelistBypass headless creators directly from git master
# (Fixes the periodic disconnects / "slot binding killed" bug in v0.3.8)
#

set -euo pipefail

DEST_DIR="${1:-/opt/whitelist-bypass/bin}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[+] Cloning latest kulikov0/whitelist-bypass..."
git clone --depth 1 https://github.com/kulikov0/whitelist-bypass.git "$TMP_DIR/wlb"

mkdir -p "$DEST_DIR"

for creator in telemost vk wbstream dion; do
    src_dir="$TMP_DIR/wlb/headless/$creator"
    if [[ -d "$src_dir" ]]; then
        echo "[+] Building headless-$creator-creator..."
        (cd "$src_dir" && go build -ldflags="-s -w" -o "$DEST_DIR/headless-$creator-creator" .)
        chmod +x "$DEST_DIR/headless-$creator-creator"
        echo "[OK] Built $DEST_DIR/headless-$creator-creator"
    fi
done

echo "[+] All creators successfully built and installed to $DEST_DIR"
