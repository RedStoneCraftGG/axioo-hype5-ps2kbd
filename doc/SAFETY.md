# Safety, recovery, and diagnostics

The keyboard bridge is experimental. It accesses legacy x86 I/O ports and unbinds the kernel `i8042` driver. Treat it like a hardware-level workaround, not an ordinary desktop utility.

## Minimum precautions

- Keep a working USB keyboard attached.
- Test from a live USB session before installing to disk.
- Do not run two instances at once.
- Do not run `ps2raw` while `ps2kbd.py` is active.
- Do not enable the systemd unit at boot until manual start, stop, and reboot behavior have been tested.
- Do not use this on a system where the touchpad, auxiliary PS/2 device, or another controller function depends on the same `i8042` driver without verifying the effects.

## Read-only first checks

```bash
uname -a
cat /proc/cmdline
cat /proc/bus/input/devices
cat /proc/interrupts
sudo dmesg | grep -Ei 'i8042|atkbd|serio|keyboard'
```

If the normal kernel driver works after a kernel update or parameter change, prefer that solution and do not run the bridge.

## Recovery

1. Use the USB keyboard to stop the foreground process with `Ctrl+C`, or send `SIGTERM` to its process.
2. If started with systemd, run `sudo systemctl stop ps2kbd.service`.
3. Check `systemctl status ps2kbd.service` and `sudo dmesg | tail -100`.
4. If the internal keyboard does not return, reboot. Avoid repeatedly unbinding and rebinding the controller.

The program attempts cleanup on normal exit and common signals, but a kernel crash, power loss, forced kill (`SIGKILL`), Python failure, or hardware quirk can bypass or defeat cleanup.

## Invasive diagnostics

`scripts/ps2raw.c` issues commands such as keyboard reset and controller commands. It is not read-only. `scripts/apicdump.py` reads ACPI tables and accesses `/dev/mem` to inspect IOAPIC registers; it may fail or be restricted by the kernel. Run neither tool unless you understand what it changes or reads and have a recovery path.

The original diagnosis notes include experiments involving driver unbind/bind and raw controller commands. Those commands are intentionally not presented as a copy-and-paste troubleshooting sequence here because the wrong sequence can interrupt input or alter controller state.

## Uninstall

Stop and disable the service if it was enabled:

```bash
sudo systemctl disable --now ps2kbd.service
```

Remove installed files:

```bash
sudo rm -f /etc/systemd/system/ps2kbd.service
sudo rm -f /usr/local/bin/ps2kbd.py
sudo rm -rf /usr/local/share/doc/ps2kbd
sudo systemctl daemon-reload
```

The installer may add `/etc/modules-load.d/uinput.conf`; remove it only if it was created by this project and you no longer want `uinput` loaded automatically:

```bash
sudo rm -f /etc/modules-load.d/uinput.conf
```
