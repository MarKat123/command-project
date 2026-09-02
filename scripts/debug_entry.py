"""
Debug helper: runs a single radiocontrol entry-point function directly under
the debugger. The installed console scripts (p5.exe, setCW.exe, ...) are
compiled launcher stubs that debugpy cannot attach through, so this calls
the same function they call, in-process, where breakpoints work normally.

Usage: python scripts/debug_entry.py <function_name>
"""
import sys

import radiocontrol

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: debug_entry.py <function_name>")

    name = sys.argv[1]
    func = getattr(radiocontrol, name, None)
    if func is None:
        sys.exit(f"radiocontrol has no function named '{name}'")

    func()
