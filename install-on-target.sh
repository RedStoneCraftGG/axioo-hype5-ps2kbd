#!/usr/bin/env bash
# Copy files only. This script deliberately does not enable/start the service.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify the installed Linux system; aborting." >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi
if [[ ! -f "$ROOT_DIR/scripts/ps2kbd.py" || ! -f "$ROOT_DIR/systemd/ps2kbd.service" ]]; then
  echo "Run this installer from the extracted repository directory." >&2
  exit 1
fi

echo "WARNING: experimental code; it unbinds i8042 and accesses /dev/port."
echo "The installer will copy files only. It will NOT start or enable the service."
read -r -p 'Continue copying files? Type YES: ' answer
[[ "$answer" == "YES" ]] || { echo "Cancelled."; exit 0; }

install -D -m 0755 "$ROOT_DIR/scripts/ps2kbd.py" /usr/local/bin/ps2kbd.py
install -D -m 0644 "$ROOT_DIR/README.md" /usr/local/share/doc/ps2kbd/README.md
install -D -m 0644 "$ROOT_DIR/doc/SAFETY.md" /usr/local/share/doc/ps2kbd/SAFETY.md
install -D -m 0644 "$ROOT_DIR/systemd/ps2kbd.service" /etc/systemd/system/ps2kbd.service
if [[ ! -e /etc/modules-load.d/uinput.conf ]]; then
  printf '%s\n' 'uinput' > /etc/modules-load.d/uinput.conf
  chmod 0644 /etc/modules-load.d/uinput.conf
else
  echo "Keeping existing /etc/modules-load.d/uinput.conf unchanged."
fi
systemctl daemon-reload

cat <<'EOF'
Files copied. The service has NOT been started or enabled.
Read /usr/local/share/doc/ps2kbd/SAFETY.md before proceeding.
After a manual live-session test, you may start it explicitly with:
  sudo systemctl start ps2kbd.service
Stop it with:
  sudo systemctl stop ps2kbd.service
Do not enable it at boot until recovery behavior is verified.
EOF
