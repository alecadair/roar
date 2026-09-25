#!/usr/bin/env python3
"""Top-level launcher for the ROAR GUI application."""

import os
import sys


def main() -> int:
    gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")
    sys.path.insert(0, gui_dir)

    import roar_gui

    return roar_gui.main()


if __name__ == "__main__":
    raise SystemExit(main())

