# Axioo Hype 5 AMD X3 — Linux internal keyboard workaround

**Status: experimental, hardware-specific, not a universal Linux keyboard driver.**

This cleaned-up repository is based on the original implementation attributed to AgentOne. The documentation, service lifecycle, installer behavior, and selected error handling have been revised; the hardware-specific polling approach remains experimental.

This repository documents a userspace polling workaround for one reported configuration: **Axioo Hype 5 AMD X3**, Zorin OS / Ubuntu 24.04-based live environment, Linux kernel `6.14.0-33-generic`. The reported test results below come from the original project notes and have not been independently reproduced on other machines or distributions.

> **Safety warning:** `ps2kbd.py` accesses x86 I/O ports through `/dev/port` and temporarily unbinds the kernel `i8042` driver. A mistake, crash, suspend/resume, or incompatible controller can leave the internal keyboard unavailable until recovery or reboot. Keep a working USB keyboard available. Do not install it as an automatically enabled boot service on an untested system.

## What it does

On the reported laptop, the internal PS/2 keyboard reportedly produced scancodes when the controller was polled, while the normal kernel `i8042`/`atkbd` path did not deliver usable keyboard data. The workaround:

1. unbinds the platform `i8042` driver;
2. polls controller ports `0x64` and `0x60` from userspace;
3. translates a subset of Set-1 scancodes to Linux keycodes;
4. emits key events through `/dev/uinput` as a virtual keyboard.

This bypasses the normal IRQ-driven path; it does **not** fix the kernel driver or the underlying firmware/interrupt issue. It also does not establish that the same issue or solution applies to other Axioo models.

## Compatibility

- **Reported target:** Axioo Hype 5 AMD X3, x86-64, Linux kernel `6.14.0-33-generic` in a Zorin/Ubuntu 24.04-based environment.
- **Other Ubuntu/Debian/Arch/Fedora/openSUSE systems:** unverified. Python and systemd are widely available, but that does not make direct controller access portable.
- **GNOME, KDE, Xorg, Wayland, XFCE, Cinnamon:** the virtual keyboard uses the Linux input subsystem, so the desktop environment should not matter once events reach `/dev/uinput`. This is an architectural expectation, not a tested compatibility claim.
- **ARM, non-i8042 keyboards, USB keyboards, and laptops with different embedded-controller designs:** not supported by this implementation.

The separate touchpad clickpad helper uses `xinput` and is **Xorg-only**. It is not part of the keyboard bridge and is not needed for keyboard operation.

## Repository layout

```text
.
├── README.md
├── LICENSE-STATUS.md
├── .gitignore
├── scripts/
│   ├── ps2kbd.py              # experimental keyboard polling bridge
│   ├── ps2raw.c               # low-level controller diagnostic; invasive
│   ├── apicdump.py            # ACPI MADT / IOAPIC diagnostic; privileged
│   └── touchpad-click.sh      # optional Xorg clickpad setting helper
├── systemd/
│   └── ps2kbd.service         # manual opt-in service; not enabled by installer
├── doc/
│   ├── trackpad-clickpad-fix.md
│   └── SAFETY.md
└── install-on-target.sh       # copies files only; does not enable the service
```

## Requirements

- x86-64 Linux with an i8042-compatible controller and a keyboard that emits compatible Set-1 scancodes after controller translation;
- Python 3;
- kernel `uinput` support and `/dev/uinput`;
- root privileges for direct port access and driver unbind/bind;
- a working external keyboard and a way to recover the system.

The current code assumes the x86-64 Linux `struct input_event` layout. Do not treat it as architecture-independent.

## Before trying it

1. Confirm that the internal keyboard is actually the problem and that the laptop's kernel logs show an `i8042`/`atkbd` issue.
2. Prefer kernel parameters, a targeted kernel quirk, or a proper kernel-driver fix if one resolves the issue. This workaround is a last resort.
3. Use a live session first, with a USB keyboard attached. Do not start by enabling the service at boot.
4. Read [`doc/SAFETY.md`](doc/SAFETY.md) and inspect the scripts before running them as root.

## Manual run (experimental)

From the repository root:

```bash
sudo modprobe uinput
sudo python3 scripts/ps2kbd.py
```

Stop with `Ctrl+C` from a terminal that can receive it, or send `SIGTERM` from another terminal. A USB keyboard is strongly recommended. The program attempts to destroy its virtual device, restore the saved controller command byte, close `/dev/port`, and re-bind `i8042` when it exits; recovery is best-effort, not guaranteed.

Do **not** run multiple copies concurrently. Do not run `scripts/ps2raw.c` while the bridge is active. The diagnostic program also writes to the controller and can disrupt keyboard state.

## Optional systemd service

The service is provided for users who have already validated the workaround on their own machine. The installer only copies the unit; it does not enable or start it.

```bash
sudo systemctl daemon-reload
sudo systemctl start ps2kbd.service
sudo systemctl status ps2kbd.service
sudo journalctl -u ps2kbd.service -f
```

Only after testing manual start/stop and reboot recovery should you consider enabling it at boot:

```bash
sudo systemctl enable ps2kbd.service
```

To stop and disable it:

```bash
sudo systemctl disable --now ps2kbd.service
```

If the internal keyboard fails, use a USB keyboard to stop the service. If the controller does not recover, reboot; do not repeatedly force unbind/bind operations.

## Installer

The installer copies the script, documentation, and systemd unit. It does **not** enable the service or run invasive diagnostics:

```bash
sudo ./install-on-target.sh
```

Uninstall instructions are in [`doc/SAFETY.md`](doc/SAFETY.md).

## Reported test notes (not a compatibility guarantee)

The original project notes report the following on the target laptop:

- basic letters, numbers, symbols and common punctuation;
- left/right Shift, Ctrl and Alt, Meta, Caps Lock, navigation keys and F1–F12;
- Num Lock / Scroll Lock and keyboard LED handling;
- trackpad remained available because that particular device was detected over I2C HID.

These results are specific to the reported machine and code revision. Extended scancodes, Print Screen sequences, Pause/Break, media keys, keyboard layouts, LED synchronization, suspend/resume and long-running stability need more systematic testing. `Fn` behavior is usually handled by firmware/embedded-controller logic and is not guaranteed by this bridge.

## Diagnostics

Start with read-only information:

```bash
uname -a
cat /proc/cmdline
cat /proc/bus/input/devices
sudo dmesg | grep -Ei 'i8042|atkbd|serio|keyboard'
cat /proc/interrupts
```

For a safe checklist and explanation of invasive diagnostics, see [`doc/SAFETY.md`](doc/SAFETY.md). Do not unbind `i8042` or access controller ports unless you understand the recovery procedure.

## Contributions

Please include the exact laptop model, BIOS/UEFI version if known, distro, kernel version, session type, relevant `dmesg` output, and whether the test was performed in a live session or installed system. Do not claim compatibility based only on the fact that the package installs.

## License

See [`LICENSE-STATUS.md`](LICENSE-STATUS.md). No open-source license has been assigned yet.
