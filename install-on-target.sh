#!/bin/bash
# install-on-target.sh - install the PS/2 keyboard bridge as a systemd service.
#   sudo ./install-on-target.sh
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "must be run with sudo"; exit 1
fi

if [ ! -f /etc/os-release ]; then
    echo "ERROR: this does not appear to be an installed system."; exit 1
fi

echo "== 1/6 check prerequisites"
if ! command -v python3 >/dev/null; then
    echo "ERROR: python3 not found"; exit 1
fi
if [ ! -e /dev/uinput ] && ! modprobe uinput 2>/dev/null; then
    echo "WARNING: /dev/uinput is missing and the uinput module failed to load"
    echo "  -> ensure the kernel has CONFIG_INPUT_UINPUT"
fi

echo "== 2/6 ensure the uinput module loads automatically"
echo "uinput" > /etc/modules-load.d/uinput.conf

echo "== 3/6 install script"
install -D -m755 "$HERE/scripts/ps2kbd.py" /usr/local/bin/ps2kbd.py

echo "== 4/6 install documentation"
install -D -m644 "$HERE/README.md" /usr/local/share/doc/ps2kbd/README.md

echo "== 5/6 install systemd unit"
install -D -m644 "$HERE/systemd/ps2kbd.service" /etc/systemd/system/ps2kbd.service
systemctl daemon-reload

echo "== 6/7 quick test (5 seconds)"
timeout 5 python3 /usr/local/bin/ps2kbd.py --testirq || true

echo "== 7/7 enable the service and start it now"
if systemctl enable --now ps2kbd.service; then
    echo "The ps2kbd service was successfully enabled and started."
else
    echo "ERROR: failed to enable ps2kbd.service."
    echo "Check the unit and logs with:"
    echo "  systemctl status ps2kbd.service --no-pager"
    echo "  journalctl -u ps2kbd.service -b --no-pager"
    exit 1
fi

cat <<'EOM'

============================================================
INSTALLATION COMPLETE

The service has been enabled to run automatically at boot
and has already been started in this session.

Check status:
  systemctl status ps2kbd.service --no-pager
  journalctl -u ps2kbd.service -b -n 50 --no-pager

Test the internal keyboard. If there is a problem, stop the service:
  sudo systemctl stop ps2kbd.service
  sudo python3 /usr/local/bin/ps2kbd.py --stop

To disable automatic start at boot and stop the service:
  sudo systemctl disable --now ps2kbd.service

Note: this script only enables the installed service.
Success at boot still depends on the contents of the systemd unit
and whether ps2kbd.py can initialize the controller when
the service starts.
============================================================
EOM