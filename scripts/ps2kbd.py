#!/usr/bin/env python3
"""Experimental polling bridge for one reported Axioo Hype 5 AMD X3 setup.

WARNING: accesses x86 I/O ports via /dev/port and unbinds the kernel i8042
platform driver. Use only after reading README.md and doc/SAFETY.md.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import signal
import struct
import sys
import time
from pathlib import Path

DRIVER_DIR = Path("/sys/bus/platform/drivers/i8042")
PORT_DEVICE = "/dev/port"
UINPUT_DEVICE = "/dev/uinput"
DEVICE_NAME = b"PS2 Internal Keyboard (polling)"

# Linux input_event ABI for x86-64: timeval (two 64-bit longs), type, code, value.
INPUT_EVENT = struct.Struct("<qqHHi")
EV_SYN = 0x00
EV_KEY = 0x01
EV_REP = 0x14
SYN_REPORT = 0
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_SETUP = 0x405C5503
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

RUNNING = True

# Set-1 scancode -> Linux input keycode. This is intentionally a limited map.
SET1: dict[int, int] = {}
for index in range(10):
    SET1[0x02 + index] = 2 + index       # 1..0
    SET1[0x10 + index] = 16 + index      # q..p
for index in range(9):
    SET1[0x1E + index] = 30 + index     # a..l
for index in range(7):
    SET1[0x2C + index] = 44 + index     # z..m
for index in range(10):
    SET1[0x3B + index] = 59 + index     # F1..F10
for index in range(13):
    SET1[0x47 + index] = 71 + index     # keypad keys
SET1.update({
    0x01: 1, 0x0C: 12, 0x0D: 13, 0x0E: 14, 0x0F: 15,
    0x1A: 26, 0x1B: 27, 0x1C: 28, 0x1D: 29,
    0x27: 39, 0x28: 40, 0x29: 41, 0x2A: 42,
    0x2B: 43, 0x33: 51, 0x34: 52, 0x35: 53,
    0x36: 54, 0x37: 55, 0x38: 56, 0x39: 57,
    0x3A: 58, 0x45: 69, 0x46: 70, 0x57: 87, 0x58: 88,
})
EXTENDED: dict[int, int] = {
    0x1C: 96, 0x1D: 97, 0x35: 98, 0x37: 99, 0x38: 100,
    0x46: 119, 0x47: 102, 0x48: 103, 0x49: 104,
    0x4B: 105, 0x4D: 106, 0x4F: 107, 0x50: 108,
    0x51: 109, 0x52: 110, 0x53: 111, 0x5B: 125,
    0x5C: 126, 0x5D: 127, 0x5E: 116,
}
LOCK_KEYS = {58, 69, 70}  # Caps Lock, Num Lock, Scroll Lock


def write_sysfs(path: Path, value: str) -> None:
    """Write a sysfs control and raise on failure (do not silently continue)."""
    with path.open("w", encoding="ascii") as handle:
        handle.write(value)


def wait_input_buffer_empty(port_fd: int, timeout_ms: int = 250) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while read_port(port_fd, 0x64) & 0x02:
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.0005)
    return True


def read_port(port_fd: int, port: int) -> int:
    os.lseek(port_fd, port, os.SEEK_SET)
    data = os.read(port_fd, 1)
    if len(data) != 1:
        raise OSError(f"short read from I/O port 0x{port:02x}")
    return data[0]


def write_port(port_fd: int, port: int, value: int) -> None:
    os.lseek(port_fd, port, os.SEEK_SET)
    if os.write(port_fd, bytes((value & 0xFF,))) != 1:
        raise OSError(f"short write to I/O port 0x{port:02x}")


def controller_command(port_fd: int, command: int) -> bool:
    if not wait_input_buffer_empty(port_fd):
        return False
    write_port(port_fd, 0x64, command)
    return True


def controller_data(port_fd: int, value: int) -> bool:
    if not wait_input_buffer_empty(port_fd):
        return False
    write_port(port_fd, 0x60, value)
    return True


def read_bytes(port_fd: int, count: int = 1, timeout_ms: int = 500) -> list[int]:
    result: list[int] = []
    deadline = time.monotonic() + timeout_ms / 1000
    while len(result) < count and time.monotonic() < deadline:
        if read_port(port_fd, 0x64) & 0x01:
            result.append(read_port(port_fd, 0x60))
        else:
            time.sleep(0.0005)
    return result


def read_command_byte(port_fd: int) -> int | None:
    if not controller_command(port_fd, 0x20):
        return None
    response = read_bytes(port_fd, 1, 250)
    return response[0] if response else None


def flush_output_buffer(port_fd: int) -> None:
    for _ in range(256):
        if not (read_port(port_fd, 0x64) & 0x01):
            break
        read_port(port_fd, 0x60)


def create_virtual_keyboard() -> int:
    fd = os.open(UINPUT_DEVICE, os.O_WRONLY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(fd, UI_SET_EVBIT, EV_REP)
        for keycode in set(SET1.values()) | set(EXTENDED.values()):
            fcntl.ioctl(fd, UI_SET_KEYBIT, keycode)
        setup = struct.pack("<HHHH80sI", 0x11, 1, 1, 1, DEVICE_NAME, 0)
        fcntl.ioctl(fd, UI_DEV_SETUP, setup)
        fcntl.ioctl(fd, UI_DEV_CREATE, 0)
        time.sleep(0.4)
        return fd
    except BaseException:
        os.close(fd)
        raise


def emit_key(fd: int, keycode: int, value: int) -> None:
    os.write(fd, INPUT_EVENT.pack(0, 0, EV_KEY, keycode, value))
    os.write(fd, INPUT_EVENT.pack(0, 0, EV_SYN, SYN_REPORT, 0))


def send_led_state(port_fd: int, locks: dict[int, bool]) -> None:
    led_mask = (4 if locks[58] else 0) | (2 if locks[69] else 0) | (1 if locks[70] else 0)
    if controller_data(port_fd, 0xED):
        read_bytes(port_fd, 1, 200)  # keyboard ACK, if present
        if controller_data(port_fd, led_mask):
            read_bytes(port_fd, 1, 200)


def request_stop(_signum: int, _frame: object) -> None:
    global RUNNING
    RUNNING = False


def main() -> int:
    global RUNNING
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="print raw scancodes")
    args = parser.parse_args()

    if os.geteuid() != 0:
        parser.error("must run as root (for /dev/port and i8042 unbind/bind)")
    if not os.path.exists(UINPUT_DEVICE):
        print("ERROR: /dev/uinput is missing; try `sudo modprobe uinput`.", file=sys.stderr)
        return 1
    if not (DRIVER_DIR / "unbind").exists() or not (DRIVER_DIR / "bind").exists():
        print("ERROR: expected i8042 platform driver sysfs controls were not found.", file=sys.stderr)
        return 1

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, request_stop)

    port_fd: int | None = None
    uinput_fd: int | None = None
    original_command_byte: int | None = None
    unbound = False
    try:
        print("WARNING: unbinding i8042; external keyboard and recovery path required.", flush=True)
        write_sysfs(DRIVER_DIR / "unbind", "i8042")
        unbound = True
        time.sleep(0.4)
        port_fd = os.open(PORT_DEVICE, os.O_RDWR | os.O_SYNC)

        flush_output_buffer(port_fd)
        original_command_byte = read_command_byte(port_fd)
        if original_command_byte is None:
            raise RuntimeError("could not read the original i8042 command byte")

        # Preserve the original byte for cleanup; set translation and disable keyboard IRQ.
        configured_byte = (original_command_byte | 0x40) & ~0x01
        if not controller_command(port_fd, 0x60) or not controller_data(port_fd, configured_byte):
            raise RuntimeError("failed to configure the i8042 command byte")

        flush_output_buffer(port_fd)
        if not controller_data(port_fd, 0xFF):
            raise RuntimeError("could not send keyboard reset command")
        reset_reply = read_bytes(port_fd, 2, 1500)
        print(f"Keyboard reset response: {' '.join(f'{b:02x}' for b in reset_reply) or '(none)'}", flush=True)
        flush_output_buffer(port_fd)
        if controller_data(port_fd, 0xF4):
            read_bytes(port_fd, 1, 500)
        flush_output_buffer(port_fd)

        uinput_fd = create_virtual_keyboard()
        print("Virtual keyboard created. Press Ctrl+C to stop.", flush=True)
        extended_prefix = False
        pause_bytes = 0
        locks = {58: False, 69: False, 70: False}

        while RUNNING:
            status = read_port(port_fd, 0x64)
            if not (status & 0x01):
                time.sleep(0.0008)
                continue
            scancode = read_port(port_fd, 0x60)
            if args.verbose:
                print(f"scancode: {scancode:02x}", flush=True)

            if pause_bytes:
                pause_bytes -= 1
                continue
            if scancode == 0xE1:
                pause_bytes = 5
                extended_prefix = False
                continue
            if scancode == 0xE0:
                extended_prefix = True
                continue
            # 0xAA must NOT be discarded: on this path it can be left-Shift release.
            if scancode in (0xFA, 0xEE):
                extended_prefix = False
                continue

            keycode = (EXTENDED if extended_prefix else SET1).get(scancode & 0x7F)
            released = bool(scancode & 0x80)
            extended_prefix = False
            if keycode is None:
                continue
            emit_key(uinput_fd, keycode, 0 if released else 1)
            if keycode in LOCK_KEYS and not released:
                locks[keycode] = not locks[keycode]
                send_led_state(port_fd, locks)

        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        if uinput_fd is not None:
            try:
                fcntl.ioctl(uinput_fd, UI_DEV_DESTROY, 0)
            except OSError as exc:
                print(f"Warning: could not destroy uinput device: {exc}", file=sys.stderr)
            try:
                os.close(uinput_fd)
            except OSError:
                pass
        if port_fd is not None and original_command_byte is not None:
            try:
                if controller_command(port_fd, 0x60) and controller_data(port_fd, original_command_byte):
                    print("Restored saved i8042 command byte.", flush=True)
                else:
                    print("Warning: could not restore i8042 command byte.", file=sys.stderr)
            except OSError as exc:
                print(f"Warning: command-byte restoration failed: {exc}", file=sys.stderr)
        if port_fd is not None:
            try:
                os.close(port_fd)
            except OSError:
                pass
        if unbound:
            try:
                write_sysfs(DRIVER_DIR / "bind", "i8042")
                print("Requested i8042 re-bind; verify keyboard recovery.", flush=True)
            except OSError as exc:
                print(f"CRITICAL: i8042 re-bind failed: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
