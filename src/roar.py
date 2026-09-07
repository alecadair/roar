#!/usr/bin/env python3
"""Top-level launcher for the ROAR GUI application."""

import os
import subprocess
import sys


def _show_env_error() -> None:
    """Show a popup (or stderr fallback) explaining how to initialize ROAR."""
    message = (
        "ROAR_HOME is not set.\n\n"
        "Please source ROAR's environment setup script before launching:\n"
        "  source $ROAR_HOME/roar_env.csh"
    )

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ROAR Environment Not Set", message)
        root.destroy()
    except Exception:
        # Fallback for headless systems where a GUI dialog cannot be shown.
        print(message, file=sys.stderr)


def main() -> int:
    roar_home = os.environ.get("ROAR_HOME")
    if not roar_home:
        _show_env_error()
        return 1

    gui_script = os.path.join(roar_home, "src", "gui", "roar_gui.py")
    if not os.path.isfile(gui_script):
        print(f"ROAR GUI launcher not found: {gui_script}", file=sys.stderr)
        return 1

    result = subprocess.run([sys.executable, gui_script], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

