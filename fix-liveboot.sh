#!/usr/bin/env bash

# Experimental Axioo Linux fix - Live Boot mode
# Keyboard and touchpad are handled independently.

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
KEYBOARD_SCRIPT="$SCRIPT_DIR/scripts/ps2kbd.py"

# Change this to the actual touchpad ID from `xinput list`.
TRACKPAD_ID="${TRACKPAD_ID:-13}"

KEYBOARD_OK=0
TRACKPAD_OK=0

echo "======================================"
echo " Axioo Linux Fix - Live Boot Mode"
echo "======================================"
echo

# --- 1. Keyboard workaround ---
echo "[1/2] Starting PS/2 keyboard workaround..."

if [[ ! -f "$KEYBOARD_SCRIPT" ]]; then
    echo "[ERROR] Keyboard script not found: $KEYBOARD_SCRIPT"
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[ERROR] Python 3 is not installed."
    elif sudo -v; then
        if sudo python3 "$KEYBOARD_SCRIPT" --bg; then
            echo "[OK] Keyboard command completed successfully."
            KEYBOARD_OK=1
        else
            echo "[ERROR] Keyboard workaround failed."
            echo "[FALLBACK] Check the error above."
            echo "Do not automatically retry in background."
            echo "Use the script's documented recovery procedure."
        fi
    else
        echo "[ERROR] Administrator authentication failed."
    fi
fi

echo

# --- 2. Touchpad click method ---
echo "[2/2] Configuring touchpad click method..."

if ! command -v xinput >/dev/null 2>&1; then
    echo "[ERROR] xinput is not installed."
    echo "[FALLBACK] Skip touchpad configuration."
elif [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
    echo "[SKIP] Wayland session detected."
    echo "[FALLBACK] Configure click method in desktop settings."
elif [[ -z "${DISPLAY:-}" ]]; then
    echo "[SKIP] DISPLAY is not set."
    echo "[FALLBACK] Run this script from the graphical Xorg session."
elif ! xinput list-props "$TRACKPAD_ID" >/dev/null 2>&1; then
    echo "[ERROR] Device ID $TRACKPAD_ID was not found."
    echo "[FALLBACK] Run 'xinput list' and set TRACKPAD_ID correctly."
elif ! xinput list-props "$TRACKPAD_ID" |
     grep -Fq 'libinput Click Method Enabled'; then
    echo "[ERROR] Click Method property is unavailable."
    echo "[FALLBACK] Check the selected device and libinput driver."
elif xinput set-prop "$TRACKPAD_ID" \
     "libinput Click Method Enabled" 1 0; then
    echo "[OK] Touchpad click method configured."
    TRACKPAD_OK=1
else
    echo "[ERROR] Could not configure touchpad."
    echo "[FALLBACK] Restore settings through desktop controls."
fi

echo
echo "======================================"
echo " Results"
echo "======================================"

if (( KEYBOARD_OK )); then
    echo "Keyboard: command accepted"
else
    echo "Keyboard: FAILED or NOT STARTED"
fi

if (( TRACKPAD_OK )); then
    echo "Touchpad: command accepted"
else
    echo "Touchpad: FAILED or SKIPPED"
fi

echo
echo "Note: command success does not prove hardware functionality."
echo "Test the keyboard and touchpad manually."
echo "======================================"