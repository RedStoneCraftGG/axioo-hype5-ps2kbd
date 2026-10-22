#!/bin/bash
# touchpad-click.sh - configure the click method for the Axioo Hype 5 clickpad.
#
#   ./touchpad-click.sh buttonareas   -> right-click = one-finger click in the bottom-right corner
#   ./touchpad-click.sh clickfinger   -> right-click = two-finger click
#   ./touchpad-click.sh status        -> show the current settings
#
# Run from an Xorg desktop session:  bash touchpad-click.sh buttonareas
MODE="${1:-status}"
export DISPLAY="${DISPLAY:-:0}"

if [ "$MODE" = "status" ]; then
    echo "DISPLAY=$DISPLAY"
    xinput list --short 2>/dev/null | grep -i touchpad || { echo "no touchpad found in xinput"; exit 1; }
    ID=$(xinput list --id-only "PNP0C50:00 093A:0255 Touchpad" 2>/dev/null)
    [ -z "$ID" ] && { echo "touchpad target not found by exact name"; exit 1; }
    echo "touchpad ID = $ID"
    xinput list-props "$ID" 2>/dev/null | grep -Ei 'Click Method Enabled|Tapping Enabled \(|Natural Scrolling|Scroll Method Enabled \('
    exit 0
fi

case "$MODE" in
    buttonareas) VALUE="1 0" ;;
    clickfinger) VALUE="0 1" ;;
    *) echo "Usage: $0 [buttonareas|clickfinger|status]"; exit 1 ;;
esac

ID=$(xinput list --id-only "PNP0C50:00 093A:0255 Touchpad" 2>/dev/null)
if [ -z "$ID" ]; then
    echo "touchpad device not found in xinput"; exit 1
fi

if xinput set-prop "$ID" "libinput Click Method Enabled" $VALUE 2>/dev/null; then
    echo "OK: Click Method = [$MODE]  (id=$ID)"
    xinput list-props "$ID" | grep 'Click Method Enabled ('
else
    echo "set-prop failed (the driver rejected value $VALUE)"
    exit 1
fi
