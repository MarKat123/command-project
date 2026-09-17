"""
Standalone panadapter power (SS04) widget for the Yaesu FTDX10 / FT-710.

Meant to be left running in its own small console window, anchored to the
upper-right of the screen, alongside the panadapter display.

Design:
- Reads the current spectrum scope power level once at startup, then tracks
  it locally and pushes an absolute set command on every +/- keypress rather
  than re-reading from the rig each time.
- Keystrokes only affect the rig while this console window has OS keyboard
  focus - true for free, since msvcrt.getch()/kbhit() only ever see input
  when this window is the foreground one. Nothing special needed for that.
- On regaining focus (switching back to this window after using something
  else), the local value is resynced with one fresh read, in case the rig's
  own menu was used to change it while this window was in the background.

Run this from a standalone Command Prompt window, not VS Code's integrated
terminal or Windows Terminal - both host console apps through ConPTY, which
doesn't support the legacy window-resize/position APIs used here and will
corrupt the terminal's rendering if they're not skipped (see
_running_under_conpty()). It still runs under those hosts, just without the
window positioning.
"""
import ctypes
import msvcrt
import os
import subprocess
import time

import radiocontrol as rc

MIN_POWER = -30.0
MAX_POWER = 30.0
STEP = 0.5
POLL_INTERVAL = 0.15  # seconds between focus/keypress checks while idle


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SM_CXSCREEN = 0


def _console_hwnd():
    return ctypes.windll.kernel32.GetConsoleWindow()


def _has_focus() -> bool:
    hwnd = _console_hwnd()
    return bool(hwnd) and ctypes.windll.user32.GetForegroundWindow() == hwnd


def _running_under_conpty() -> bool:
    """
    Windows Terminal and VS Code's integrated terminal both host console
    apps through ConPTY, a pseudo-console layer that doesn't support the
    legacy console resize/window APIs used below - calling them there
    corrupts the terminal's rendering instead of doing anything useful.
    Detected via the environment markers both of them set.
    """
    return bool(os.environ.get("WT_SESSION")) or os.environ.get("TERM_PROGRAM") == "vscode"


def _position_window():
    """Shrinks this console to a small fixed size and anchors it to the
    upper-right corner of the primary monitor. One-time placement only -
    not re-enforced if you drag the window afterward. No-op under a
    ConPTY-hosted terminal - see _running_under_conpty()."""
    if _running_under_conpty():
        print("Running under a ConPTY-hosted terminal (VS Code / Windows Terminal) -")
        print("skipping window resize/positioning to avoid corrupting it.")
        print("Run from a standalone Command Prompt window for full behavior.\n")
        return

    subprocess.run("mode con: cols=40 lines=3", shell=True)

    hwnd = _console_hwnd()
    if not hwnd:
        return

    rect = _RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left

    screen_width = ctypes.windll.user32.GetSystemMetrics(_SM_CXSCREEN)
    x = screen_width - width
    y = 0
    ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, _SWP_NOSIZE | _SWP_NOZORDER)


def _format_value(value: float) -> str:
    return f"{value:+05.1f}"


def getpanpower():
    """Reads the current spectrum scope power level from the rig, or None on comm error."""
    response = rc.send_rig("W SS04; 10")
    if response is None or len(response) < 9:
        return None
    return float(response[4:9])


def setpanpower(value: float) -> float:
    """Clamps/snaps value and sends it to the rig as an absolute set command."""
    value = max(MIN_POWER, min(MAX_POWER, value))
    value = round(value * 2) / 2  # snap to the nearest 0.5dB step
    rc.send_rig(f"W SS04{_format_value(value)}; 0")
    return value


def _display(value: float):
    print(f"\rAmp: {_format_value(value)} dB   ", end="", flush=True)


def run():
    _position_window()

    value = getpanpower()
    if value is None:
        print("Couldn't read current panadapter power from the rig - starting from 0.0")
        value = 0.0

    print("PA widget: '+'/'-'")
    _display(value)

    was_focused = _has_focus()

    while True:
        now_focused = _has_focus()
        if now_focused and not was_focused:
            fresh = getpanpower()
            if fresh is not None:
                value = fresh
                _display(value)
        was_focused = now_focused

        if not msvcrt.kbhit():
            time.sleep(POLL_INTERVAL)
            continue

        key = msvcrt.getch()
        try:
            key = key.decode()
        except UnicodeDecodeError:
            continue

        if key in ('+', '='):
            value = setpanpower(value + STEP)
        elif key in ('-', '_'):
            value = setpanpower(value - STEP)
        elif key in ('q', 'Q', '\x1b'):
            break
        else:
            continue

        _display(value)

    print()
    rc.close_socket()
    return


if __name__ == "__main__":
    run()
