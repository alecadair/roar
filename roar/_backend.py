"""Lazy access to the legacy backend (no Qt imports at package import time)."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import signal
import sys
import threading
from types import ModuleType


def backend_directory() -> Path:
    """Locate either the checkout GUI or the wheel's mapped legacy package."""
    package = Path(__file__).resolve().parent
    for candidate in (package.parent / "src" / "gui", package / "_legacy"):
        if (candidate / "equation_solver.py").is_file():
            return candidate
    raise FileNotFoundError("ROAR legacy backend is missing from the checkout/wheel")


def resolve_home(home: Path | str | None = None) -> Path:
    """Resolve assets/LUT home; explicit home wins over ROAR_HOME and checkout."""
    selected = home if home is not None else os.environ.get("ROAR_HOME")
    if selected:
        result = Path(selected).expanduser().resolve()
        if not result.is_dir():
            raise FileNotFoundError(f"ROAR home is not a directory: {result}")
        return result
    checkout = Path(__file__).resolve().parent.parent
    if (checkout / "tech_list.txt").is_file():
        return checkout
    raise FileNotFoundError("Set ROAR_HOME or pass home= to locate ROAR assets and LUTs")


def prepare_backend(home: Path | str | None = None) -> Path:
    """Initialize legacy paths only when a solver or live session is requested."""
    root = resolve_home(home)
    backend = backend_directory()
    values = {
        "ROAR_HOME": str(root),
        "ROAR_SRC": str(backend.parent if backend.name == "gui" else backend),
        "ROAR_LIB": str(root / "lib"),
        "ROAR_DEPENDENCIES": str(root / "dependencies"),
        "ROAR_CHARACTERIZATION": str(root / "characterization"),
        "ROAR_DESIGN": str(root / "design"),
    }
    os.environ.update(values)
    # Notebook kernels can inherit a backend unavailable outside Jupyter. Do not
    # discard user-selected Agg/Qt/etc. backends.
    if "inline" in os.environ.get("MPLBACKEND", "").lower():
        os.environ.pop("MPLBACKEND", None)
    directory = str(backend)
    if directory not in sys.path:
        sys.path.insert(0, directory)  # legacy siblings use absolute imports
    # Legacy modules cache paths at import time. Honor a later explicit home.
    for name in ("roar_gui", "design_editor", "roar_console"):
        module = sys.modules.get(name)
        if module is not None:
            for key, value in values.items():
                if hasattr(module, key):
                    setattr(module, key, value)
            if hasattr(module, "ROAR_DESIGN_SCRIPTS"):
                module.ROAR_DESIGN_SCRIPTS = values["ROAR_DESIGN"]
    return root


def load_backend(module: str, home: Path | str | None = None) -> ModuleType:
    """Import a legacy sibling without replacing the caller's SIGINT handler."""
    if not module.isidentifier():
        raise ValueError("Expected a legacy module name, e.g. 'equation_solver'")
    prepare_backend(home)
    main_thread = threading.current_thread() is threading.main_thread()
    if module == "roar_gui" and not main_thread:
        raise RuntimeError("The ROAR GUI must be loaded on the main thread")
    handler = signal.getsignal(signal.SIGINT) if main_thread else None
    try:
        return importlib.import_module(module)
    finally:
        if main_thread:
            signal.signal(signal.SIGINT, handler)