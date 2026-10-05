"""Dialog-free live access to ROAR's Qt widgets.

Importing this module and constructing a hidden Session do not import Qt.
The first live operation creates/reuses QApplication on the main thread.
Graph configuration keys are the keys in Graph.to_state(), not GUI aliases.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
import csv
import math
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any

from ._backend import load_backend
from .design import Design, Graph

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication

# A process-wide strong reference: Qt must outlive widgets and temporary sessions.
_QT_APPLICATION: QApplication | None = None


@contextmanager
def _blocked(objects):
    """Restore pre-existing signal blocks, including after legacy helper errors."""
    saved = [(obj, obj.signalsBlocked()) for obj in objects]
    try:
        for obj, _ in saved:
            obj.blockSignals(True)
        yield
    finally:
        for obj, previous in reversed(saved):
            obj.blockSignals(previous)


def _main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("ROAR Qt operations must run on the main thread")


class Session:
    """A live GUI adapter for a detached Design.

    ``show=False`` is lazy. ``app=`` / ``from_app`` attach without making a
    second QApplication or changing the existing design. ``run`` is only for
    a Session that created QApplication; embedded hosts drive their own loop.
    """

    def __init__(self, design: Design | None = None, *, home: Path | str | None = None,
                 show: bool = False, app: Any = None):
        if design is not None and not isinstance(design, Design):
            raise TypeError("design must be a Design")
        self.home = home
        self._initial_design = design
        self._app = app
        self._qapp = None
        self._backend = None
        self._owns_qapp = False
        self._owns_window = app is None
        self._closed = False
        if app is not None:
            self._attach()
            if design is not None:
                self.apply(design)
                self._initial_design = None
        if show:
            self.show()

    @classmethod
    def from_app(cls, app: Any) -> Session:
        """Attach to an existing ROARApp without restoring or constructing it."""
        return cls(app=app)

    def _attach(self) -> None:
        _main_thread()
        from PyQt6.QtCore import QThread
        from PyQt6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if not isinstance(qapp, QApplication):
            raise RuntimeError("An existing QApplication is required")
        if QThread.currentThread() != qapp.thread() or self._app.thread() != qapp.thread():
            raise RuntimeError("ROARApp and QApplication must belong to the current thread")
        if not all(hasattr(self._app, key) for key in ("capture_app_state", "editor_window", "graph_tabs")):
            raise TypeError("app must be an existing ROARApp")
        global _QT_APPLICATION
        _QT_APPLICATION = self._qapp = qapp

    def _ensure(self) -> None:
        _main_thread()
        if self._closed:
            raise RuntimeError("Session is closed")
        if self._app is not None:
            self._attach()
            return
        self._backend = load_backend("roar_gui", self.home)
        from PyQt6.QtCore import QThread
        from PyQt6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp is not None and not isinstance(qapp, QApplication):
            raise RuntimeError("A non-GUI QCoreApplication already exists")
        if qapp is None:
            qapp = QApplication(["roar"])
            self._owns_qapp = True
        if QThread.currentThread() != qapp.thread():
            raise RuntimeError("QApplication belongs to another thread")
        global _QT_APPLICATION
        _QT_APPLICATION = self._qapp = qapp
        self._app = self._backend.ROARApp()
        initial, self._initial_design = self._initial_design, None
        if initial is not None:
            self.apply(initial)

    @property
    def app(self):
        """The live ROARApp (access launches the lazy session)."""
        self._ensure()
        return self._app

    def _module(self):
        if self._backend is None:
            self._backend = load_backend("roar_gui", self.home)
        return self._backend

    def apply(self, design: Design) -> Session:
        """Restore tables/tabs without progress dialogs or showing/maximizing."""
        if not isinstance(design, Design):
            raise TypeError("design must be a Design")
        self._ensure()
        state = design.to_state()
        app = self._app
        tabs_state = state.get("graph_tabs", {})
        tabs = tabs_state.get("tabs", [])
        for tab in tabs:
            if not isinstance(tab.get("name"), str) or tab["name"] == "+":
                raise ValueError("Graph tabs need a name other than '+'")
            indices = [window.get("index") for window in tab.get("windows", [])]
            if any(type(i) is not int or not 0 <= i < 4 for i in indices) or len(set(indices)) != len(indices):
                raise ValueError("Window indices must be unique integers in 0..3")
        current = tabs_state.get("current_tab_index", 0)
        if type(current) is not int or (tabs and not 0 <= current < len(tabs)):
            raise ValueError("current_tab_index must select a real graph tab")
        editor = app.editor_window
        previous = app._is_restoring_state
        app._is_restoring_state = True
        try:
            with _blocked([app.graph_tabs, editor, editor.expression_editor,
                           editor.constraint_editor.tree, editor.instance_table.tree]):
                timer = getattr(editor, "_expressions_changed_timer", None)
                if timer is not None:
                    timer.stop()
                data = state.get("design_editor", {})
                editor.expression_editor.load_table_data(data.get("expression_editor", []),
                                                         data.get("expression_tabs"))
                for key in ("constraint_editor", "instance_table"):
                    getattr(editor, key).load_table_data(data.get(key, []))
                settings = data.get("iterative_solver")
                if settings is not None:
                    editor._get_or_create_iterative_dialog().set_settings(settings)
                symbols = editor.get_expression_symbols()
                # Build explicitly: create_new_graph_tab catches errors with a dialog.
                for i in reversed(range(app.graph_tabs.count())):
                    old = app.graph_tabs.widget(i)
                    app.graph_tabs.removeTab(i)
                    old.deleteLater()
                grids = []
                for tab in tabs:
                    grid = self._module().ROARGraphGrid(parent=app, top_level_app=app)
                    app.graph_tabs.addTab(grid, tab["name"])
                    grid.populate_from_app()
                    grids.append(grid)
                    for window in grid.lookup_windows:
                        window.update_expression_symbols(symbols)
                    # Set every window before applying locks to avoid axis callbacks
                    # resetting locks while neighbouring windows are still defaults.
                    for config in tab.get("windows", []):
                        self._apply_window(grid.lookup_windows[config["index"]], config,
                                           restore_locks=False)
                    for window in grid.lookup_windows:
                        window.update_attachment_checkboxes()
                    for config in tab.get("windows", []):
                        self._locks(grid.lookup_windows[config["index"]], config.get("locked_windows", []))
                app._graph_tab_count = len(grids)
                app.ensure_plus_tab()
                if grids:
                    app.graph_tabs.setCurrentIndex(current)
                    app.graph_grid = grids[current]
                else:
                    app.graph_grid = None
                app._sync_all_instance_browser_tabs()
                theme = state.get("theme", "light")
                if theme not in ("light", "dark"):
                    raise ValueError("theme must be 'light' or 'dark'")
                app.set_theme(theme)
                dock = getattr(app, "python_dock", None)
                if dock is not None:
                    from PyQt6.QtCore import Qt
                    panel = state.get("console_panel", {})
                    dock.setFloating(bool(panel.get("floating", False)))
                    if not dock.isFloating():
                        app.addDockWidget(Qt.DockWidgetArea(panel.get("area", 2)), dock)
                    dock.setVisible(bool(panel.get("visible", False)))
                geometry = state.get("window", {}).get("geometry")
                if geometry:
                    app.setGeometry(*(int(geometry.get(k, v)) for k, v in
                                      (("x", 100), ("y", 100), ("width", 1200), ("height", 800))))
                # Deliberately ignore 'maximized': apply must not display a window.
        finally:
            app._is_restoring_state = previous
        return self

    @staticmethod
    def _locks(window, indices) -> None:
        checkboxes = window.setting_checkboxes
        if any(type(i) is not int or not 0 <= i < len(checkboxes) for i in indices):
            raise ValueError("Invalid locked_windows index")
        with _blocked(checkboxes):
            for i, checkbox in enumerate(checkboxes):
                checkbox.setChecked(i in indices)

    def _apply_window(self, window, config, *, restore_locks=True) -> None:
        config = deepcopy(config)
        device_mode = config.get("is_device_params_mode", True)
        symbols = self._app.editor_window.get_expression_symbols()
        allowed = self._app.lookups if device_mode else symbols
        # Reject caller mistakes before mutating controls or erasing the plot.
        for axis in "xyz":
            text = config.get(f"combo_{axis}_text", "")
            if not text and axis in "xy":
                raise ValueError(f"Missing {axis} axis selection")
            if text and text not in allowed:
                raise ValueError(f"Unknown {axis} axis: {text!r}")
        paths = config.get("checked_paths", [])
        for path in paths:
            item = window.tech_browser.path_to_item.get(path)
            if item is None or item.childCount():
                raise ValueError(f"Unknown/non-corner checked path: {path!r}")
        locks = config.get("locked_windows", [])
        if any(type(i) is not int or not 0 <= i < len(window.setting_checkboxes) for i in locks):
            raise ValueError("Invalid locked_windows index")
        for marker in config.get("markers", []):
            pos = float(marker["linear_pos"])
            vertical = marker.get("vertical", True)
            if not math.isfinite(pos):
                raise ValueError("Marker position must be finite")
            if config.get("checkbox_logx" if vertical else "checkbox_logy", False) and pos <= 0:
                raise ValueError("Log-axis markers require positive linear positions")
        controls = [window.radio_device_params, window.radio_design_eq, window.tech_browser.tree]
        controls += [getattr(window, name) for name in config
                     if name.startswith("checkbox_") and hasattr(window, name)]
        controls += [getattr(window, f"{kind}_{axis}") for kind in ("combo", "spin")
                     for axis in "xyz" if hasattr(window, f"{kind}_{axis}")]
        controls += list(window.setting_checkboxes)
        # The legacy helper swallows exceptions and unblocks widgets internally;
        # validate before/after it and restore signal/flag states in our finally.
        previous = window._is_updating
        startup = window.tech_browser.startup
        markers = config.pop("markers", [])
        locks = config.pop("locked_windows", [])
        try:
            with _blocked(controls):
                window._is_updating = True
                window.is_device_params_mode = device_mode
                # update_combobox_items reads the radio, not the mode flag.
                window.radio_device_params.setChecked(window.is_device_params_mode)
                window.radio_design_eq.setChecked(not window.is_device_params_mode)
                window.expression_symbols = symbols
                window.update_combobox_items()
                for axis in "xyz":
                    key = f"combo_{axis}_text"
                    text = config.get(key, "")
                    combo = getattr(window, f"combo_{axis}", None)
                    if text and combo is not None and combo.findText(text) < 0:
                        raise ValueError(f"Unknown {axis} axis: {text!r}")
                if not window.is_device_params_mode:
                    solver = load_backend("equation_solver", self.home).ROAREquationSolver(self._app)
                    expressions, _ = self._app.editor_window.get_expressions_and_constraints()
                    for symbol, expression in expressions.items():
                        error = solver.add_equation(symbol, expression)
                        if error:
                            raise ValueError(f"Invalid expression {symbol!r}: {error}")
                self._app._restore_lookup_window_state(window, dict(config, markers=[], locked_windows=[]))
                # Its internal helpers unconditionally unblock these widgets.
                for control in controls:
                    control.blockSignals(True)
                for axis in "xyz":
                    text = config.get(f"combo_{axis}_text", "")
                    if text and getattr(window, f"combo_{axis}").currentText() != text:
                        raise ValueError(f"Backend did not restore {axis} axis {text!r}")
                if set(window.tech_browser.get_checked_item_paths()) != set(paths):
                    raise ValueError("Backend did not restore checked corner paths exactly")
                if hasattr(window, "checkbox_legend"):
                    window.checkbox_legend.setChecked(bool(config.get("checkbox_legend", False)))
                window._update_z_controls_state()
                if not config.get("checkbox_3d", False) and window.gl_widget is not None:
                    window.gl_widget.hide()
                    window.plot_widget.show()
                window.clear_markers()
                window._is_updating = False
                window.update_graph_from_tech_browser()
                # Legacy refresh can leave stale log modes on an empty plot.
                window.plot_widget.getPlotItem().setLogMode(
                    x=bool(config.get("checkbox_logx", False)),
                    y=bool(config.get("checkbox_logy", False)))
                self._legend(window, bool(config.get("checkbox_legend", False)))
                for marker in markers:
                    self._add_marker(window, marker["linear_pos"], marker.get("vertical", True))
                if restore_locks:
                    self._locks(window, locks)
        finally:
            window._is_updating = previous
            window.tech_browser.startup = startup

    @staticmethod
    def _legend(window, visible) -> None:
        plot = window.plot_widget.getPlotItem()
        legend = plot.legend
        if visible and legend is None:
            legend = plot.addLegend()
            for curve in plot.curves:
                if curve.name():
                    legend.addItem(curve, curve.name())
        if legend is not None:
            legend.setVisible(visible)
        # Current legacy GUI no longer has the checkbox, so capture must use this.
        window._session_legend_visible = visible

    @staticmethod
    def _add_marker(window, pos, vertical):
        pos = float(pos)
        if not math.isfinite(pos):
            raise ValueError("Marker position must be finite")
        plot = window.plot_widget
        axis = plot.getPlotItem().getAxis("bottom" if vertical else "left")
        if axis.logMode and pos <= 0:
            raise ValueError("Log-axis markers require positive linear positions")
        fn = plot.add_vertical_marker if vertical else plot.add_horizontal_marker
        fn(linear_pos=pos, sync=False)
        return len(plot.line_markers) - 1

    def capture(self) -> Design:
        """Capture a deep-copy, detached public model."""
        state = self.app.capture_app_state()
        for tab, grid in zip(state["graph_tabs"]["tabs"], self._grids()):
            for config in tab["windows"]:
                window = grid.lookup_windows[config["index"]]
                if hasattr(window, "_session_legend_visible"):
                    config["checkbox_legend"] = window._session_legend_visible
        return Design.from_state(state)

    def save(self, path):
        return self.capture().save(path)

    def export_design(self, path):
        return self.capture().export_design(path)

    def export_python(self, path):
        return self.capture().export_python(path)

    def export_spice(self, path):
        return self.capture().export_spice(path)

    def export_solver_python(self, path) -> Path:
        """Export the GUI's computational script, without its file/error dialogs."""
        editor = self.app.editor_window
        expressions, constraints = editor.get_expressions_and_constraints()
        script = load_backend("roar_console", self.home).export_design_to_python(
            expressions=expressions, constraints=constraints,
            instances=editor.instance_table.get_table_data(),
            device_corners=editor.get_device_corners())
        target = Path(path)
        target.write_text(script, encoding="utf-8")
        return target

    def _grids(self):
        return [self._app.graph_tabs.widget(i) for i in range(self._app.graph_tabs.count())
                if self._app.graph_tabs.tabText(i) != "+"]

    def _grid(self, tab):
        app = self.app
        if isinstance(tab, str):
            matches = [app.graph_tabs.widget(i) for i in range(app.graph_tabs.count())
                       if app.graph_tabs.tabText(i) == tab and tab != "+"]
            if len(matches) != 1:
                raise ValueError(f"Unknown or ambiguous graph tab: {tab!r}")
            return matches[0]
        grids = self._grids()
        if type(tab) is not int or not 0 <= tab < len(grids):
            raise IndexError("Graph tab index out of range")
        return grids[tab]

    def graph(self, tab: int | str = 0, index: int = 0) -> LiveGraph:
        self._grid(tab)
        if type(index) is not int or not 0 <= index < 4:
            raise IndexError("Graph window index must be in 0..3")
        return LiveGraph(self, tab, index)

    def refresh(self, tab: int | str | None = None) -> Session:
        """Publish editor symbols and refresh all windows, or one named/indexed tab."""
        self._ensure()
        grids = self._grids() if tab is None else [self._grid(tab)]
        for grid in grids:
            for index in range(len(grid.lookup_windows)):
                # _apply_window publishes the new symbols after validating the
                # existing selections; don't silently replace deleted axes.
                LiveGraph(self, self._grids().index(grid), index).refresh()
        return self

    def show(self) -> Session:
        self.app.show()
        return self

    def run(self) -> int:
        self._ensure()
        from PyQt6.QtCore import QThread
        if not self._owns_qapp or QThread.currentThread().loopLevel():
            raise RuntimeError("The host owns/runs Qt's event loop; use show() instead")
        self.show()
        return self._qapp.exec()

    def close(self) -> None:
        _main_thread()
        if not self._closed and self._app is not None:
            self._app.close()
            if self._owns_window:
                dialog = getattr(self._app.editor_window, "_iterative_solver_dialog", None)
                if dialog is not None:
                    dialog.close()
                self._app.deleteLater()
        self._closed = True

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class LiveGraph:
    """One live lookup window. ``widget`` exposes all legacy operations.

    Marker values are linear nearest-sample readouts (not interpolated). CSV
    exports original curve samples, before log transforms/downsampling, with
    one row per sample and curve/corner identifiers. set_range uses linear
    coordinates, converting positive log-axis bounds to view coordinates.
    3-D range setting is unsupported by the legacy normalized GL camera.
    """

    def __init__(self, session: Session, tab: int | str, index: int):
        self.session, self.tab, self.index = session, tab, index

    @property
    def widget(self):
        return self.session._grid(self.tab).lookup_windows[self.index]

    def to_state(self) -> dict:
        window = self.widget
        config = self.session.app._capture_lookup_window_state(window)
        config["index"] = self.index
        config["checkbox_legend"] = getattr(window, "_session_legend_visible", config["checkbox_legend"])
        return deepcopy(config)

    def configure(self, **kwargs) -> LiveGraph:
        """Apply Graph.to_state() keys to only this window; reject unknown keys."""
        config = self.to_state()
        unknown = set(kwargs) - set(config)
        if unknown:
            raise TypeError(f"Unknown graph configuration keys: {sorted(unknown)}")
        if "index" in kwargs and kwargs["index"] != self.index:
            raise ValueError("configure cannot move a graph to another window")
        config.update(kwargs)
        self.session._apply_window(self.widget, config)
        return self

    def apply(self, graph: Graph) -> LiveGraph:
        """Apply a detached Graph configuration to this live window."""
        config = graph.to_state()
        config["index"] = self.index
        return self.configure(**config)

    def copy_to(self, other: LiveGraph, *, copy_attachments: bool = False) -> LiveGraph:
        """Copy saved plot settings/2-D markers; keep destination locks by default."""
        if not isinstance(other, LiveGraph):
            raise TypeError("other must be a LiveGraph")
        if type(copy_attachments) is not bool:
            raise TypeError("copy_attachments must be a bool")
        config = self.to_state()
        config.pop("index")
        config["index"] = other.index
        if not copy_attachments:
            config.pop("locked_windows")
        return other.configure(**config)

    def set_browser_mode(self, mode: str) -> LiveGraph:
        """Set the GUI browser role, without synthesizing a corner-change event."""
        window = self.widget
        if mode not in ("global", "local", "follower"):
            raise ValueError("Browser mode must be 'global', 'local', or 'follower'")
        if mode == "global":
            window._set_global(True)
        elif mode == "local":
            window._set_local(True)
        else:
            window._set_global(False)
            window._set_local(False)
        return self

    @staticmethod
    def _validate_corner(window, path) -> None:
        if not isinstance(path, str):
            raise ValueError("Corner paths must be full GUI leaf-path strings")
        item = window.tech_browser.path_to_item.get(path)
        if item is None or item.childCount():
            raise ValueError(f"Unknown/non-corner checked path: {path!r}")

    def _corner_colors(self, colors) -> dict:
        window = self.widget
        if not isinstance(colors, Mapping):
            raise TypeError("colors must be a path-to-color mapping")
        from PyQt6.QtGui import QColor
        result = self.to_state()["color_map"]
        for path, color in colors.items():
            self._validate_corner(window, path)
            if not isinstance(color, str) or not color or not QColor(color).isValid():
                raise ValueError("Color must be a valid CSS/Qt color string")
            result[path] = color
        return result

    def _sync_browser_followers(self) -> None:
        window = self.widget
        if window._is_global_browser and window.graph_grid:
            paths = window.tech_browser.get_checked_item_paths()
            colors = dict(window.tech_browser.color_map)
            for other in window.graph_grid.lookup_windows:
                if other is not window:
                    # sync_from_global unconditionally unblocks its tree.
                    previous = other._is_updating
                    try:
                        with _blocked([other.tech_browser.tree]):
                            other.sync_from_global(paths, colors)
                    finally:
                        other._is_updating = previous

    def select_corners(self, paths, colors=None) -> LiveGraph:
        """Select exact GUI leaf paths, retaining colors not explicitly replaced."""
        window = self.widget
        paths = [paths] if isinstance(paths, str) else list(paths)
        for path in paths:
            self._validate_corner(window, path)
        if len(set(paths)) != len(paths):
            raise ValueError("Corner selections cannot contain duplicates")
        config = {"checked_paths": paths}
        if colors is not None:
            config["color_map"] = self._corner_colors(colors)
        self.configure(**config)
        self._sync_browser_followers()
        return self

    def set_color(self, path: str, color: str) -> LiveGraph:
        """Color a known corner without changing the checked selection."""
        self.configure(color_map=self._corner_colors({path: color}))
        self._sync_browser_followers()
        return self

    def lock(self, indices) -> LiveGraph:
        """Replace exact attachment indices, without copying/syncing markers."""
        window = self.widget
        indices = list(indices)
        if any(type(i) is not int or not 0 <= i < len(window.setting_checkboxes)
               for i in indices):
            raise ValueError("Invalid locked_windows index")
        if len(set(indices)) != len(indices):
            raise ValueError("Locked window indices cannot contain duplicates")
        return self.configure(locked_windows=indices)

    def refresh(self) -> LiveGraph:
        self.session._apply_window(self.widget, self.to_state())
        return self

    def add_marker(self, pos, vertical: bool = True) -> int:
        self._require_2d()
        return self.session._add_marker(self.widget, pos, vertical)

    def clear_markers(self) -> LiveGraph:
        self.widget.clear_markers()
        return self

    def marker_values(self, index: int = 0) -> list[dict]:
        self._require_2d()
        plot = self.widget.plot_widget
        if type(index) is not int or not 0 <= index < len(plot.line_markers):
            raise IndexError("Marker index out of range")
        values = plot.get_marker_curve_values(plot.line_markers[index])
        if not isinstance(values, list) or any(
            not isinstance(row, dict) or not {"curve_idx", "corner_path", "corner_name", "x", "y"} <= row.keys()
            or not all(math.isfinite(float(row[axis])) for axis in "xy") for row in values
        ):
            raise ValueError("Backend returned malformed/non-finite marker readouts")
        return deepcopy(values)

    def _require_3d(self):
        window = self.widget
        if not window.checkbox_3d.isChecked():
            raise NotImplementedError("This operation requires a 3-D graph")
        gl = window.gl_widget
        if gl is None:
            raise RuntimeError("The 3-D OpenGL widget is unavailable")
        if self.session._qapp.platformName().lower() in ("offscreen", "minimal"):
            raise RuntimeError("3-D controls require a real display/OpenGL context, not offscreen Qt")
        return gl

    def add_point_marker(self, x, y, z, corner: str | None = None) -> int:
        """Pick the nearest finite rendered sample in linear XYZ space.

        corner matches the GL surface label, not a full technology path.
        Repeated picks of the same sample/label return the existing index.
        """
        gl = self._require_3d()
        import numpy as np
        target = np.asarray([float(x), float(y), float(z)], dtype=float)
        if not np.isfinite(target).all():
            raise ValueError("Point marker coordinates must be finite")
        window = self.widget
        if any(getattr(window, f"checkbox_log{axis}").isChecked() and value <= 0
               for axis, value in zip("xyz", target)):
            raise ValueError("Log-axis point markers require positive linear coordinates")
        if corner is not None and (not isinstance(corner, str) or not corner):
            raise ValueError("corner must be a nonempty surface label or None")
        originals = gl._all_orig_points
        normals = gl._all_norm_points
        if not originals or not normals:
            raise RuntimeError("Show and render the 3-D graph before picking: no rendered samples")
        if len(originals) != len(normals):
            raise RuntimeError("Malformed rendered 3-D sample arrays")
        labels = gl._all_point_labels
        best = None
        best_distance = math.inf
        matched = False
        for surface, (orig, norm) in enumerate(zip(originals, normals)):
            label = labels[surface] if surface < len(labels) else f"surface {surface}"
            if corner is not None and corner != label:
                continue
            matched = True
            orig, norm = np.asarray(orig, dtype=float), np.asarray(norm, dtype=float)
            if orig.shape != norm.shape or orig.ndim != 2 or orig.shape[1] != 3:
                raise RuntimeError("Malformed rendered 3-D sample arrays")
            if len(orig) == 0:
                continue
            with np.errstate(over="ignore", invalid="ignore"):
                linear = np.asarray([gl._display_orig(point) for point in orig])
                distances = np.hypot.reduce(linear - target, axis=1)
            valid = np.isfinite(linear).all(axis=1) & np.isfinite(norm).all(axis=1)
            distances[~valid] = math.inf
            sample = int(np.argmin(distances))
            if distances[sample] < best_distance:
                best_distance = float(distances[sample])
                best = (surface, norm[sample].copy(), orig[sample].copy(), label)
        if not matched:
            raise ValueError(f"Unknown rendered surface label: {corner!r}")
        if best is None:
            raise RuntimeError("No finite rendered 3-D samples; show and render the graph before picking")
        surface, norm, orig, label = best
        for index, marker in enumerate(gl._3d_point_markers):
            if marker.get("corner_name") == label and np.array_equal(marker["pos_orig"], orig):
                return index
        colors = gl._all_point_colors
        color = colors[surface] if surface < len(colors) else (1.0, 0.0, 0.0, 1.0)
        previous = getattr(gl, "_last_pick_label", None)
        index = len(gl._3d_point_markers)
        try:
            gl._last_pick_label = label
            gl.add_point_marker(norm, orig, surface_color=color)
        finally:
            gl._last_pick_label = previous
        if len(gl._3d_point_markers) != index + 1:
            raise RuntimeError("The OpenGL backend could not create a 3-D point marker")
        return index

    def point_marker_values(self, index: int = 0) -> dict:
        """Return a 3-D point marker's physical x/y/z and rendered surface label."""
        gl = self._require_3d()
        if type(index) is not int or not 0 <= index < len(gl._3d_point_markers):
            raise IndexError("Point marker index out of range")
        marker = gl._3d_point_markers[index]
        linear = gl._display_orig(marker["pos_orig"])
        values = {axis: float(value) for axis, value in zip("xyz", linear)}
        if len(linear) != 3 or not all(math.isfinite(value) for value in values.values()):
            raise ValueError("Backend returned malformed/non-finite point marker readouts")
        values["label"] = marker.get("corner_name") or "corner"
        return values

    def set_camera(self, distance=None, elevation=None, azimuth=None, center=None) -> LiveGraph:
        """Set the live GL camera; center is in normalized GL coordinates, not SI."""
        gl = self._require_3d()
        from PyQt6.QtGui import QVector3D
        options = {}
        for name, value in (("distance", distance), ("elevation", elevation), ("azimuth", azimuth)):
            if value is not None:
                value = float(value)
                if not math.isfinite(value) or (name == "distance" and value <= 0):
                    raise ValueError("Camera parameters must be finite; distance must be positive")
                options[name] = value
        if center is not None:
            try:
                if isinstance(center, (str, bytes)):
                    raise ValueError("center must be a coordinate sequence")
                coordinates = tuple(map(float, center))
            except (TypeError, ValueError) as exc:
                raise ValueError("Camera center must contain three finite GL coordinates") from exc
            if len(coordinates) != 3 or not all(math.isfinite(value) for value in coordinates):
                raise ValueError("Camera center must contain three finite GL coordinates")
            vector = QVector3D(*coordinates)
            if not all(math.isfinite(value) for value in (vector.x(), vector.y(), vector.z())):
                raise ValueError("Camera center exceeds the finite QVector3D coordinate range")
            options["pos"] = vector
        if options:
            gl.setCameraPosition(**options)
        return self

    def assign(self, instance, attr, value=None, marker=0, reduce="mean",
               source_label=None, as_column=True) -> dict:
        """Assign a literal or marker's free-axis value using the GUI attribute spec.

        reduce: mean, min, max, or 'corner:<corner name/path>'. When value is
        omitted a vertical marker supplies Y and a horizontal marker supplies X.
        Corner paths are retained as keys to avoid collapsing duplicate names.
        """
        table = self.session.app.editor_window.instance_table
        item = table.find_instance_item(instance)
        if item is None:
            raise KeyError(f"Unknown instance: {instance!r}")
        attr = str(attr).strip()
        if not attr:
            raise ValueError("Attribute name cannot be empty")
        per_corner = {}
        if value is None:
            rows = self.marker_values(marker)
            if not rows:
                raise ValueError("Marker does not intersect any plotted curve")
            vertical = self.widget.plot_widget.line_markers[marker]["vertical"]
            axis = "y" if vertical else "x"
            per_corner = {row["corner_path"] or f"{row['corner_name']}#{row['curve_idx']}": row[axis] for row in rows}
            numbers = [row[axis] for row in rows]
            if reduce == "mean":
                value = sum(numbers) / len(numbers)
            elif reduce == "min":
                value = min(numbers)
            elif reduce == "max":
                value = max(numbers)
            elif isinstance(reduce, str) and reduce.startswith("corner:"):
                key = reduce.partition(":")[2]
                selected = [row[axis] for row in rows if key in (row["corner_path"], row["corner_name"])]
                if len(selected) != 1:
                    raise ValueError("Corner selector must match exactly one curve")
                value = selected[0]
            else:
                raise ValueError("reduce must be mean, min, max, or corner:<name/path>")
            if source_label is None:
                pinned = "x" if vertical else "y"
                source_label = f"{getattr(self.widget, 'combo_' + axis).currentText()} at {getattr(self.widget, 'combo_' + pinned).currentText()}={rows[0][pinned]:g}"
        else:
            reduce = "literal"
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Assigned values must be finite")
        if as_column and attr not in table.columns:
            table.add_column(attr)
        spec = {"mode": "pinned", "resolved": value, "reduce": reduce,
                "per_corner": per_corner, "source_label": source_label,
                "as_column": attr in table.columns}
        table.set_instance_attribute(item, attr, spec)
        return deepcopy(spec)

    def set_range(self, x=None, y=None, z=None) -> LiveGraph:
        if z is not None or self.widget.checkbox_3d.isChecked():
            raise NotImplementedError("3-D axis ranges are not supported by the legacy GL camera")
        plot = self.widget.plot_widget.getPlotItem()
        ranges = {}
        for axis, bounds in (("x", x), ("y", y)):
            if bounds is None:
                continue
            low, high = map(float, bounds)
            if not math.isfinite(low) or not math.isfinite(high) or low >= high:
                raise ValueError("Range bounds must be finite and increasing")
            if plot.getAxis("bottom" if axis == "x" else "left").logMode:
                if low <= 0:
                    raise ValueError("Log ranges require positive linear bounds")
                low, high = math.log10(low), math.log10(high)
            ranges[axis + "Range"] = (low, high)
        plot.setRange(padding=0, **ranges)
        return self

    def autofit(self) -> LiveGraph:
        if self.widget.checkbox_3d.isChecked():
            self.widget.auto_fit_3d()
        else:
            self.widget.plot_widget.getPlotItem().autoRange()
        return self

    def reset(self) -> LiveGraph:
        self.widget.reset_window()
        self.session._locks(self.widget, [])
        self.session._legend(self.widget, False)
        return self

    def expand(self) -> LiveGraph:
        if not self.widget.is_expanded:
            self.widget.expand_plot()
        return self

    def contract(self) -> LiveGraph:
        if self.widget.is_expanded:
            self.widget.contract_plot()
        return self

    def _require_2d(self) -> None:
        if self.widget.checkbox_3d.isChecked():
            raise NotImplementedError("This operation supports 2-D plots only")

    def export_png(self, path) -> Path:
        window = self.widget
        target = Path(path)
        if window.checkbox_3d.isChecked():
            if self.session._qapp.platformName().lower() in ("offscreen", "minimal"):
                raise RuntimeError("3-D PNG capture requires a real display/OpenGL context, not offscreen Qt")
            gl = window.gl_widget
            if gl is None or not gl.isVisible():
                raise RuntimeError("Show and render the 3-D graph before capturing PNG")
            image = gl.grabFramebuffer()
            if image.isNull() or not image.save(str(target), "PNG"):
                raise RuntimeError("Could not capture the 3-D OpenGL framebuffer")
        else:
            from pyqtgraph.exporters import ImageExporter
            ImageExporter(window.plot_widget.getPlotItem()).export(str(target))
        return target

    def export_svg(self, path) -> Path:
        self._require_2d()
        from pyqtgraph.exporters import SVGExporter
        target = Path(path)
        SVGExporter(self.widget.plot_widget.getPlotItem()).export(str(target))
        return target

    def export_csv(self, path) -> Path:
        """Original linear samples; never synthetic indices or log10 values."""
        self._require_2d()
        plot = self.widget.plot_widget.getPlotItem()
        target = Path(path)
        with target.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["curve_idx", "curve_name", "corner_path", "x", "y"])
            for i, curve in enumerate(plot.curves):
                if hasattr(curve, "getOriginalDataset"):
                    xdata, ydata = curve.getOriginalDataset()
                else:
                    xdata, ydata = curve.getData()
                    if xdata is not None and plot.getAxis("bottom").logMode:
                        xdata = 10.0 ** xdata
                    if ydata is not None and plot.getAxis("left").logMode:
                        ydata = 10.0 ** ydata
                if xdata is None or ydata is None:
                    continue
                if len(xdata) != len(ydata):
                    raise ValueError("Curve X/Y arrays have different lengths")
                writer.writerows((i, curve.name() or "", curve.property("corner_path") or "", float(x), float(y))
                                 for x, y in zip(xdata, ydata))
        return target