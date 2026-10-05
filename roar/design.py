"""Detached design and plot models using the GUI's native JSON schema.

No third-party dependencies, Qt imports, process-global setup, or file dialogs
are required to create/edit/save/export designs. Mutators return self to allow
chaining. Getters return deep copies; use named mutators to change the model.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import math
from pathlib import Path
from pprint import pformat
from typing import Any


def _name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Names must be nonempty strings")
    return value.strip()


def _text(value: Any) -> str:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Values must be finite")
    return str(value)


def _write(path, content: str) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _corners(paths):
    from .evaluation import _path
    if paths is None:
        return None
    if isinstance(paths, str):
        paths = [paths]
    data = []
    for value in paths:
        path = _path(value["path"] if isinstance(value, dict) else value)
        _, pdk, model, length, corner = path.split(">")
        data.append({"name": corner, "path": path, "pdk": pdk, "model": model, "length": length})
    if not data:
        raise ValueError("Custom corners cannot be empty; use None for global corners")
    if len({row["path"] for row in data}) != len(data):
        raise ValueError("Corner selections cannot contain duplicates")
    return data


def _new_graph(index: int) -> dict:
    return {"index": index, "is_device_params_mode": True,
            "combo_x_text": "kgm", "combo_y_text": "kcgs", "combo_z_text": "iden",
            "spin_x_value": 0, "spin_y_value": 0, "spin_z_value": 0,
            "checkbox_logx": False, "checkbox_logy": False, "checkbox_logz": False,
            "checkbox_3d": False, "checkbox_contour": False,
            "checkbox_legend": False, "checkbox_black_bg": False,
            "locked_windows": [index], "checked_paths": [], "color_map": {}, "markers": []}


class Design:
    """A design plus four-window graph tabs; independent of the desktop GUI.

    add_* raises on duplicate names. set_* updates existing named rows. Disabled
    rows and GUI plot flags are preserved on round trips. Global instance
    corners are None; explicit corners use full Technology Browser leaf paths.
    """

    def __init__(self, name: str = "Design"):
        self._state = {"version": "1.0.2", "app_name": "ROAR",
                       "window": {"geometry": {"x": 100, "y": 100, "width": 1200, "height": 800},
                                  "maximized": False}, "theme": "light",
                       "console_panel": {"visible": False, "floating": False, "area": 2},
                       "design_editor": {"expression_editor": [], "constraint_editor": [], "instance_table": [],
                                         "iterative_solver": {"enabled": False, "max_iterations": 50,
                                                              "tolerance": 1e-6, "damping": 1.0,
                                                              "initial_guesses": {}}},
                       "graph_tabs": {"current_tab_index": 0, "tabs": []}}
        self.add_tab(name)

    @classmethod
    def from_state(cls, state: dict) -> Design:
        """Load a native application state or design-only editor dictionary.

        Unknown state keys are preserved for forwards compatibility. JSON
        serializability and duplicate row/tab names are checked immediately.
        Syntax/numerical checking happens through evaluate(), not save().
        """
        if not isinstance(state, dict):
            raise TypeError("state must be a dictionary")
        state = json.loads(json.dumps(state, allow_nan=False))
        design = cls()
        if "design_editor" not in state and any(k in state for k in ("expression_editor", "instance_table", "constraint_editor")):
            state = {"design_editor": state}
        for key, value in state.items():
            if key == "design_editor":
                if not isinstance(value, dict):
                    raise ValueError("design_editor must be a dictionary")
                design._state[key].update(value)
            else:
                design._state[key] = value
        for kind, column in (("expression", "Symbol"), ("constraint", "Symbol"), ("instance", "Instance")):
            rows = design._rows(kind)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ValueError(f"{kind} rows must be a list of dictionaries")
            names = [_name(row.get(column, "")) for row in rows]
            if len(set(names)) != len(names):
                raise ValueError(f"Duplicate {kind} names")
        tabs = design._state["graph_tabs"]["tabs"]
        names = [_name(tab["name"]) for tab in tabs]
        if len(set(names)) != len(names) or "+" in names:
            raise ValueError("Graph tab names must be unique and cannot be '+'")
        for tab in tabs:
            windows = tab.get("windows", [])
            indices = [window.get("index") for window in windows]
            if any(type(i) is not int or not 0 <= i < 4 for i in indices) or len(set(indices)) != len(indices):
                raise ValueError("Window indices must be unique integers in 0..3")
            tab["windows"] = [dict(_new_graph(i), **next((w for w in windows if w["index"] == i), {})) for i in range(4)]
        selected = design._state["graph_tabs"].get("current_tab_index", 0)
        if type(selected) is not int or (tabs and not 0 <= selected < len(tabs)):
            raise ValueError("Invalid selected graph tab")
        return design

    @classmethod
    def load(cls, path) -> Design:
        return cls.from_state(json.loads(Path(path).expanduser().read_text(encoding="utf-8")))

    def to_state(self) -> dict:
        return deepcopy(self._state)

    def save(self, path) -> Path:
        state = self.to_state()
        state["saved_at"] = datetime.now().isoformat()
        return _write(path, json.dumps(state, indent=2, allow_nan=False) + "\n")

    def export_design(self, path) -> Path:
        """Export only editor inputs/solver settings, as the GUI's design JSON."""
        return _write(path, json.dumps(self._state["design_editor"], indent=2, allow_nan=False) + "\n")

    def export_python(self, path) -> Path:
        """Export a runnable Python script reproducing ALL inputs/graphs.

        The exported script defaults to a sibling .roar file; accepts --output
        and --show. It imports roar, not a checkout-specific internal module.
        """
        state = self.to_state()
        state.pop("saved_at", None)
        literal = pformat(state, width=100, sort_dicts=False)
        script = ('#!/usr/bin/env python3\n"""ROAR API design reconstruction (trusted inputs)."""\n'
                  'import argparse\nfrom pathlib import Path\nimport roar\n\n'
                  f'def build_design():\n    return roar.Design.from_state({literal})\n\n'
                  'def main():\n    parser = argparse.ArgumentParser(description=__doc__)\n'
                  '    parser.add_argument("--output", type=Path, default=Path(__file__).with_suffix(".roar"))\n'
                  '    parser.add_argument("--show", action="store_true")\n'
                  '    args = parser.parse_args()\n    design = build_design()\n'
                  '    print(design.save(args.output))\n'
                  '    if args.show:\n        roar.Session(design).run()\n\n'
                  'if __name__ == "__main__":\n    main()\n')
        return _write(path, script)

    def get_instance_parameters(self) -> dict:
        result = {}
        for row in self.instances:
            parameters = {attr: {"value": value, "source": "instance table"}
                          for attr, value in row.items()
                          if attr not in ("Instance", "Corners", "disabled", "plot")
                          and not attr.startswith("_") and value != ""}
            for attr, spec in row.get("_attributes", {}).items():
                value = spec.get("resolved")
                if value is not None and value != "":
                    parameters[attr] = {"value": value, "source": spec.get("source_label", "assigned"),
                                        "reduce": spec.get("reduce"), "per_corner": spec.get("per_corner", {})}
            if parameters:
                result[row["Instance"]] = parameters
        return result

    def export_spice(self, path) -> Path:
        """Write assigned/table instance attributes as SPICE .param statements.

        This exports parameters, not a circuit netlist. Empty instance values
        produce a header-only file, not a popup. Sanitization collisions raise.
        """
        lines = ["* ROAR design parameter export", ""]
        used = set()
        for instance, attrs in self.get_instance_parameters().items():
            lines.append(f"* ---- Instance {instance} ----")
            for attr, info in attrs.items():
                raw = f"{instance}_{attr}".lower()
                name = "".join(c if c.isalnum() or c == "_" else "_" for c in raw)
                if name[0].isdigit():
                    name = "p_" + name
                if name in used:
                    raise ValueError(f"SPICE parameter name collision: {name}")
                used.add(name)
                value = _text(info["value"])
                if "\n" in value or "\r" in value:
                    raise ValueError("SPICE values must be single-line")
                note = f"* {attr}: {info.get('source', 'assigned')}"
                if info.get("reduce"):
                    note += f", across corners: {info['reduce']}"
                lines.append(note)
                if info.get("per_corner"):
                    lines.append("*   per-corner: " + ", ".join(f"{k}={_text(v)}" for k, v in info["per_corner"].items()))
                lines.append(f".param {name} = {value}")
            lines.append("")
        return _write(path, "\n".join(lines) + "\n")

    def _rows(self, kind: str) -> list:
        keys = {"expression": "expression_editor", "constraint": "constraint_editor", "instance": "instance_table"}
        if kind not in keys:
            raise ValueError("Row kind must be expression, constraint, or instance")
        return self._state["design_editor"][keys[kind]]

    def _row(self, kind: str, name: str) -> dict:
        key = "Instance" if kind == "instance" else "Symbol"
        name = _name(name)
        for row in self._rows(kind):
            if row[key] == name:
                return row
        raise KeyError(f"Unknown {kind}: {name!r}")

    def _add_equation(self, kind, symbol, expression, enabled, plot):
        symbol, expression = _name(symbol), _text(expression)
        if not symbol.isidentifier() or symbol.startswith("__roar_"):
            raise ValueError("Symbols must be Python identifiers outside the reserved __roar_ namespace")
        if not expression.strip():
            raise ValueError("Expression cannot be empty")
        if any(row["Symbol"] == symbol for row in self._rows(kind)):
            raise ValueError(f"Duplicate {kind}: {symbol!r}")
        column = "Expression" if kind == "expression" else "Constraint Expression"
        self._rows(kind).append({"Symbol": symbol, column: expression, "disabled": not enabled, "plot": bool(plot)})
        return self

    def add_expression(self, symbol: str, expression: Any, *, enabled=True, plot=False) -> Design:
        return self._add_equation("expression", symbol, expression, enabled, plot)

    def add_constraint(self, symbol: str, expression: str, *, enabled=True, plot=False) -> Design:
        return self._add_equation("constraint", symbol, expression, enabled, plot)

    def set_expression(self, symbol: str, expression: Any) -> Design:
        text = _text(expression)
        if not text.strip():
            raise ValueError("Expression cannot be empty")
        self._row("expression", symbol)["Expression"] = text
        return self

    def set_constraint(self, symbol: str, expression: str) -> Design:
        self._row("constraint", symbol)["Constraint Expression"] = _name(expression)
        return self

    def set_row_enabled(self, kind: str, name: str, enabled=True) -> Design:
        self._row(kind, name)["disabled"] = not enabled
        return self

    def set_row_plot(self, kind: str, name: str, plot=True) -> Design:
        self._row(kind, name)["plot"] = bool(plot)
        return self

    def remove_row(self, kind: str, name: str) -> Design:
        self._rows(kind).remove(self._row(kind, name))
        return self

    def move_row(self, kind: str, name: str, index: int) -> Design:
        rows = self._rows(kind)
        if type(index) is not int or not 0 <= index < len(rows):
            raise IndexError("Row index out of range")
        row = self._row(kind, name)
        rows.remove(row)
        rows.insert(index, row)
        return self

    @property
    def expressions(self) -> dict[str, str]:
        return {row["Symbol"]: row["Expression"] for row in self._rows("expression") if not row.get("disabled", False)}

    @property
    def constraints(self) -> dict[str, str]:
        return {row["Symbol"]: row["Constraint Expression"] for row in self._rows("constraint") if not row.get("disabled", False)}

    @property
    def instances(self) -> list[dict]:
        return deepcopy(self._rows("instance"))

    def add_instance(self, name: str, *, corners=None, enabled=True, **parameters) -> Design:
        name = _name(name)
        if not name.isidentifier():
            raise ValueError("Instance names must be identifiers for column:instance lookups")
        if any(row["Instance"] == name for row in self._rows("instance")):
            raise ValueError(f"Duplicate instance: {name!r}")
        data = _corners(corners)
        row = {"Instance": name, "Corners": "[*Global*]" if data is None else ", ".join(c["name"] for c in data),
               "kgm": "", "ID": "", "W": "", "L": "", "disabled": not enabled,
               "plot": False, "_corners_data": data}
        self._rows("instance").append(row)
        try:
            for attr, value in parameters.items():
                self.set_instance_attribute(name, attr, value)
        except Exception:
            self._rows("instance").remove(row)
            raise
        return self

    def set_instance_corners(self, name: str, corners=None) -> Design:
        data = _corners(corners)
        row = self._row("instance", name)
        row["_corners_data"] = data
        row["Corners"] = "[*Global*]" if data is None else ", ".join(c["name"] for c in data)
        return self

    def get_device_corners(self) -> dict:
        result = {}
        for row in self.instances:
            data = row.get("_corners_data")
            if data is None:
                result[row["Instance"]] = {"corners": None, "corner_paths": None, "pdk": None, "model": None, "length": None}
            else:
                result[row["Instance"]] = {"corners": [c["name"] if isinstance(c, dict) else c for c in data],
                                           "corner_paths": [c.get("path", "") if isinstance(c, dict) else "" for c in data],
                                           **{key: data[0].get(key) if data and isinstance(data[0], dict) else None
                                              for key in ("pdk", "model", "length")}}
        return result

    def set_instance_attribute(self, instance: str, attr: str, value: Any, *, source_label="API",
                               reduce="literal", per_corner=None, as_column=True) -> Design:
        attr = _name(attr)
        if attr in ("Instance", "Corners", "disabled", "plot") or attr.startswith("_"):
            raise ValueError("Reserved instance attribute name")
        row = self._row("instance", instance)
        text = _text(value)
        spec = {"mode": "pinned", "resolved": value, "source_label": str(source_label),
                "reduce": reduce, "per_corner": dict(per_corner or {}), "as_column": bool(as_column)}
        spec = json.loads(json.dumps(spec, allow_nan=False))
        row.setdefault("_attributes", {})[attr] = spec
        if as_column or attr in ("kgm", "ID", "W", "L"):
            row[attr] = text
        return self

    def clear_instance_attribute(self, instance: str, attr: str) -> Design:
        row = self._row("instance", instance)
        row.get("_attributes", {}).pop(attr, None)
        if attr in row:
            row[attr] = ""
        return self

    @property
    def iterative_settings(self) -> dict:
        return deepcopy(self._state["design_editor"]["iterative_solver"])

    def set_iterative_solver(self, *, enabled=False, max_iterations=50, tolerance=1e-6,
                             damping=1.0, initial_guesses=None) -> Design:
        if type(max_iterations) is not int or max_iterations < 1:
            raise ValueError("max_iterations must be a positive integer")
        if not math.isfinite(tolerance) or tolerance <= 0 or not math.isfinite(damping) or not 0 < damping <= 1:
            raise ValueError("tolerance must be positive and damping in (0, 1]")
        guesses = json.loads(json.dumps(dict(initial_guesses or {}), allow_nan=False))
        self._state["design_editor"]["iterative_solver"] = {
            "enabled": bool(enabled), "max_iterations": max_iterations, "tolerance": tolerance,
            "damping": damping, "initial_guesses": guesses}
        return self

    @property
    def tabs(self) -> list[dict]:
        return deepcopy(self._state["graph_tabs"]["tabs"])

    def _tab(self, tab: int | str) -> dict:
        tabs = self._state["graph_tabs"]["tabs"]
        if isinstance(tab, str):
            for item in tabs:
                if item["name"] == tab:
                    return item
            raise KeyError(f"Unknown graph tab: {tab!r}")
        if type(tab) is not int or not 0 <= tab < len(tabs):
            raise IndexError("Graph tab index out of range")
        return tabs[tab]

    def add_tab(self, name: str) -> Design:
        name = _name(name)
        if name == "+" or any(tab["name"] == name for tab in self.tabs):
            raise ValueError("Graph tab names must be unique and cannot be '+'")
        self._state["graph_tabs"]["tabs"].append({"name": name, "windows": [_new_graph(i) for i in range(4)]})
        return self

    def rename_tab(self, tab: int | str, name: str) -> Design:
        name = _name(name)
        current = self._tab(tab)
        if name == "+" or any(t["name"] == name and t is not current for t in self._state["graph_tabs"]["tabs"]):
            raise ValueError("Graph tab names must be unique and cannot be '+'")
        current["name"] = name
        return self

    def remove_tab(self, tab: int | str) -> Design:
        tabs = self._state["graph_tabs"]["tabs"]
        if len(tabs) == 1:
            raise ValueError("A design must have at least one graph tab")
        selected = tabs[self._state["graph_tabs"]["current_tab_index"]]
        tabs.remove(self._tab(tab))
        self._state["graph_tabs"]["current_tab_index"] = tabs.index(selected) if selected in tabs else 0
        return self

    def select_tab(self, tab: int | str) -> Design:
        self._state["graph_tabs"]["current_tab_index"] = self._state["graph_tabs"]["tabs"].index(self._tab(tab))
        return self

    def graph(self, tab: int | str = 0, index: int = 0) -> Graph:
        if type(index) is not int or not 0 <= index < 4:
            raise IndexError("Graph window index must be in 0..3")
        return Graph(self, self._tab(tab)["windows"][index])

    def set_window(self, *, width=1200, height=800, x=100, y=100, maximized=False,
                   theme="light", console_visible=False) -> Design:
        if theme not in ("light", "dark"):
            raise ValueError("theme must be light or dark")
        if width <= 0 or height <= 0:
            raise ValueError("Window dimensions must be positive")
        self._state["window"] = {"geometry": dict(x=int(x), y=int(y), width=int(width), height=int(height)),
                                 "maximized": bool(maximized)}
        self._state["theme"] = theme
        self._state["console_panel"]["visible"] = bool(console_visible)
        return self

    def evaluate(self, symbols=None, *, corners=None, home=None, apply_constraints=True):
        from .evaluation import evaluate_design
        return evaluate_design(self, symbols, corners=corners, home=home, apply_constraints=apply_constraints)

    def session(self, *, home=None, show=False):
        from .session import Session
        return Session(self, home=home, show=show)


class Graph:
    """A mutable view of one saved graph, owned by its Design.

    configure accepts friendly names; configure_state accepts native GUI keys.
    Marker/range positions and exported samples use linear physical units.
    3-D headless evaluation exports sample points, not the GUI meshgrid surface.
    """

    def __init__(self, design: Design, state: dict):
        self.design, self._state = design, state

    def to_state(self) -> dict:
        return deepcopy(self._state)

    def configure(self, *, x=None, y=None, z=None, mode=None, corners=None,
                  log_x=None, log_y=None, log_z=None, three_d=None, contour=None,
                  legend=None, black_background=None, spin_x=None, spin_y=None,
                  spin_z=None, locked_windows=None) -> Graph:
        values = {}
        for axis, value in (("x", x), ("y", y), ("z", z)):
            if value is not None:
                values[f"combo_{axis}_text"] = _name(value)
        for name, value in (("logx", log_x), ("logy", log_y), ("logz", log_z),
                            ("3d", three_d), ("contour", contour), ("legend", legend), ("black_bg", black_background)):
            if value is not None:
                values[f"checkbox_{name}"] = bool(value)
        for axis, value in (("x", spin_x), ("y", spin_y), ("z", spin_z)):
            if value is not None:
                values[f"spin_{axis}_value"] = float(value)
        if mode is not None:
            if mode not in ("device", "design"):
                raise ValueError("mode must be device or design")
            values["is_device_params_mode"] = mode == "device"
        if locked_windows is not None:
            values["locked_windows"] = list(locked_windows)
        self.configure_state(**values)
        if corners is not None:
            self.select_corners(corners)
        return self

    def configure_state(self, **values) -> Graph:
        unknown = set(values) - set(_new_graph(0))
        if unknown:
            raise TypeError(f"Unknown graph state keys: {sorted(unknown)}")
        if "index" in values and values["index"] != self._state["index"]:
            raise ValueError("Cannot change the window index")
        for index in values.get("locked_windows", []):
            if type(index) is not int or not 0 <= index < 4:
                raise ValueError("Locked window indices must be in 0..3")
        values = json.loads(json.dumps(values, allow_nan=False))
        self._state.update(values)
        return self

    def select_corners(self, paths, *, colors=None) -> Graph:
        from .evaluation import _path
        if isinstance(paths, str):
            paths = [paths]
        paths = [_path(path) for path in paths]
        if len(set(paths)) != len(paths):
            raise ValueError("Corner selections cannot contain duplicates")
        self._state["checked_paths"] = paths
        if colors:
            for path, color in colors.items():
                self.set_color(path, color)
        return self

    def set_color(self, path: str, color: str) -> Graph:
        from .evaluation import _path
        if not isinstance(color, str) or not color:
            raise ValueError("Color must be a CSS/Qt color string")
        self._state["color_map"][_path(path)] = color
        return self

    def add_marker(self, pos: float, *, vertical=True) -> Graph:
        pos = float(pos)
        if not math.isfinite(pos):
            raise ValueError("Marker position must be finite")
        if self._state["checkbox_logx" if vertical else "checkbox_logy"] and pos <= 0:
            raise ValueError("Log-axis markers require positive linear positions")
        self._state["markers"].append({"vertical": bool(vertical), "linear_pos": pos})
        return self

    def clear_markers(self) -> Graph:
        self._state["markers"] = []
        return self

    def remove_marker(self, index: int) -> Graph:
        if type(index) is not int or not 0 <= index < len(self._state["markers"]):
            raise IndexError("Marker index out of range")
        del self._state["markers"][index]
        return self

    def evaluate(self, *, home=None):
        from .evaluation import graph_data
        return graph_data(self.design, self, home=home)

    def export_csv(self, path, *, home=None) -> Path:
        """Export evaluated (constraint-filtered) x/y[/z] points for all corners."""
        import pandas as pd
        frames = []
        for frame in self.evaluate(home=home):
            frame = frame.copy()
            frame.insert(0, "corner", frame.attrs.get("corner"))
            frames.append(frame)
        columns = ["corner", "x", "y"] + (["z"] if self._state["checkbox_3d"] else [])
        table = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
        return _write(path, table.to_csv(index=False))

    def export_plot(self, path, *, home=None) -> Path:
        """Headless Matplotlib PNG/SVG/PDF; no display or pyplot is required."""
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        target = Path(path)
        if target.suffix.lower() not in (".png", ".svg", ".pdf"):
            raise ValueError("Plot filename must end in .png, .svg, or .pdf")
        fig = Figure(figsize=(7, 5), layout="constrained")
        FigureCanvasAgg(fig)
        axes = fig.add_subplot(111, projection="3d" if self._state["checkbox_3d"] else None)
        for frame in self.evaluate(home=home):
            label = frame.attrs.get("corner") or "Design"
            color = self._state["color_map"].get(label)
            if self._state["checkbox_3d"]:
                axes.scatter(frame.x, frame.y, frame.z, label=label, color=color, s=4)
            else:
                axes.plot(frame.x, frame.y, label=label, color=color)
        for axis in ("xyz" if self._state["checkbox_3d"] else "xy"):
            getattr(axes, f"set_{axis}label")(self._state[f"combo_{axis}_text"])
            if self._state[f"checkbox_log{axis}"]:
                getattr(axes, f"set_{axis}scale")("log")
        if not self._state["checkbox_3d"]:
            for marker in self._state["markers"]:
                fn = axes.axvline if marker["vertical"] else axes.axhline
                fn(marker["linear_pos"], color="gray", linestyle="--", linewidth=0.8)
        if self._state["checkbox_legend"] and axes.has_data():
            axes.legend(fontsize="small")
        target.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(target)
        return target