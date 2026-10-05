#!/usr/bin/env python3
"""Top-level launcher for the ROAR GUI application."""

import os
import sys


def main() -> int:
    # Preserve the historical script entry point, using the public package.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    from roar_api.__main__ import main as api_main
    return api_main()


def __getattr__(name):
    """Expose the API when older notebooks put only src on their import path."""
    import importlib
    package_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "roar_api")
    exports = {"Design": "design", "Graph": "design", "Session": "session",
               "LiveGraph": "session", "Technologies": "evaluation", "EvaluationResult": "evaluation"}
    if name == "__path__":
        return [package_dir]
    if name == "__version__":
        return "1.0.2"
    if name in ("launch", "__all__"):
        return getattr(importlib.import_module("roar_api"), name)
    if name in exports:
        return getattr(importlib.import_module(f"roar_api.{exports[name]}"), name)
    raise AttributeError(f"module 'roar' has no attribute {name!r}")


if __name__ == "__main__":
    raise SystemExit(main())

