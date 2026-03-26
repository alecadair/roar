import sys
import os
import json
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
import numpy as np
#import pyqtgraph.opengl as gl
try:
    with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
        _fh.write('roar_gui imported\n')
except Exception:
    pass

from PyQt6.QtWidgets import (
    QDoubleSpinBox, QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QSplitter, QHBoxLayout,
    QLineEdit, QLabel, QTextEdit, QCheckBox, QColorDialog, QTreeWidget, QTreeWidgetItem,
    QScrollBar, QFileDialog, QInputDialog, QComboBox, QSpinBox, QGridLayout, QSizePolicy,
    QMessageBox, QMenuBar, QMenu, QFileDialog, QStatusBar, QRadioButton, QTabBar, QAbstractItemView,
    QProgressDialog, QDialog)
from PyQt6.QtCore import Qt, QSize, QObject, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QAction, QColor, QPen, QKeySequence, QCursor
# QShortcut historically lives in QtWidgets but some PyQt6 builds expose it in QtGui.
# Import with a fallback so the module works across environments.
try:
    from PyQt6.QtWidgets import QShortcut  # preferred location
except Exception:
    try:
        from PyQt6.QtGui import QShortcut  # fallback for some builds
    except Exception:
        QShortcut = None
# QActionGroup may be exposed in QtWidgets on some builds; try QtWidgets then QtGui, else provide shim
try:
    from PyQt6.QtWidgets import QActionGroup
except Exception:
    try:
        from PyQt6.QtGui import QActionGroup
    except Exception:
        # Minimal shim for QActionGroup used in this module: we only need addAction and setExclusive
        class QActionGroup:
            def __init__(self, parent=None):
                self._actions = []
                self._exclusive = False

            def addAction(self, action):
                try:
                    action.setCheckable(True)
                except Exception:
                    pass
                self._actions.append(action)

            def setExclusive(self, exclusive):
                self._exclusive = bool(exclusive)
                if self._exclusive and self._actions:
                    # ensure only one action is checked: make first one checked if none
                    any_checked = False
                    for a in self._actions:
                        try:
                            if a.isChecked():
                                any_checked = True
                                break
                        except Exception:
                            pass
                    if not any_checked:
                        try:
                            self._actions[0].setChecked(True)
                        except Exception:
                            pass
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"

# ── Fix PyOpenGL / Qt OpenGL platform mismatch (RHEL 8/Rocky 8, Wayland) ──
# On Wayland sessions with XWayland, PyOpenGL auto-selects the EGL
# platform while Qt6 (xcb backend) creates GLX contexts.
# eglGetCurrentContext() then returns NULL even though Qt has a valid
# GLX context, causing "Attempt to retrieve context when no valid
# context" errors from OpenGL/contextdata.py.
#
# Prong 1: Set PYOPENGL_PLATFORM=x11 before PyOpenGL loads so it
#          picks GLX from the start.
# Prong 2: After import, patch contextdata.getContext() to fall back
#          to a Qt-based context ID when the native check returns NULL.
#          This handles cases where Prong 1 didn't take effect.
_wayland = bool(os.environ.get('WAYLAND_DISPLAY'))
_x11     = bool(os.environ.get('DISPLAY'))
if _wayland and _x11 and not os.environ.get('PYOPENGL_PLATFORM'):
    os.environ['PYOPENGL_PLATFORM'] = 'x11'

# from PySide6.QtCore import Qt
import pyqtgraph as pg
import pyqtgraph.opengl as gl

# Prong 2 – unconditionally patch contextdata.getContext().
# On RHEL 8 / Rocky 8, BOTH EGL and GLX GetCurrentContext() can return
# NULL when Qt manages the context internally.  We always install the
# fallback so PyOpenGL asks Qt for the context when native check fails.
try:
    from OpenGL import platform as _gl_plat
    import OpenGL.contextdata as _ctxdata
    _orig_getContext = _ctxdata.getContext

    def _patched_getContext(context=None):
        """Fall back to a Qt-derived context ID when native check fails."""
        if context is not None:
            return _orig_getContext(context)
        try:
            ctx = _gl_plat.GetCurrentContext()
            if ctx:
                return ctx
        except Exception:
            pass
        # Native platform says no context – ask Qt instead.
        # QOpenGLContext lives in QtGui (not QtOpenGL) in PyQt6.
        try:
            from PyQt6.QtGui import QOpenGLContext
            qctx = QOpenGLContext.currentContext()
            if qctx is not None:
                return id(qctx)
        except ImportError:
            pass
        # Nothing worked – call original (will raise the error).
        return _orig_getContext(context)

    _ctxdata.getContext = _patched_getContext
except Exception:
    pass
import qdarktheme

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cid import CIDDevice
from design_editor import *
from generator import *
from equation_solver import *



# Import the relocated lookup window class (try absolute, package, then relative styles)
ROARLookupWindow = None
try:
    # when running as a script with src on sys.path
    from roar_lookup_window import ROARLookupWindow as _ROARLookupWindow
    ROARLookupWindow = _ROARLookupWindow
except Exception:
    try:
        # when imported as a package (gui.roar_gui)
        from gui.roar_lookup_window import ROARLookupWindow as _ROARLookupWindow
        ROARLookupWindow = _ROARLookupWindow
    except Exception:
        try:
            # relative import as fallback
            from .roar_lookup_window import ROARLookupWindow as _ROARLookupWindow
            ROARLookupWindow = _ROARLookupWindow
        except Exception:
            ROARLookupWindow = None

# Import the Python console and code editor widgets (PyQt6-QScintilla based)
ROARConsole = None
ROARTextEditor = None
try:
    from roar_console import ROARConsole as _ROARConsole, ROARTextEditor as _ROARTextEditor
    ROARConsole = _ROARConsole
    ROARTextEditor = _ROARTextEditor
except Exception:
    try:
        from gui.roar_console import ROARConsole as _ROARConsole, ROARTextEditor as _ROARTextEditor
        ROARConsole = _ROARConsole
        ROARTextEditor = _ROARTextEditor
    except Exception:
        try:
            from .roar_console import ROARConsole as _ROARConsole, ROARTextEditor as _ROARTextEditor
            ROARConsole = _ROARConsole
            ROARTextEditor = _ROARTextEditor
        except Exception:
            ROARConsole = None
            ROARTextEditor = None

# Environment variables
ROAR_HOME = os.environ.get("ROAR_HOME", "")
ROAR_LIB = os.environ.get("ROAR_LIB", "")
ROAR_SRC = os.environ.get("ROAR_SRC", "")
ROAR_CHARACTERIZATION = os.environ.get("ROAR_CHARACTERIZATION", "")
ROAR_DESIGN_SCRIPTS = os.environ.get("ROAR_DESIGN", "")

# Module-level defaults for LUT directories (used by test harness at bottom of file).
# These mirror the values constructed inside ROARApp.__init__ so that running
# small isolated tests at module import doesn't fail with NameError.
sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
predictive_28 = ROAR_CHARACTERIZATION + "/predictive_28/LUTs_1V8_mac"
ihp130_luts = ROAR_CHARACTERIZATION + "/ihp130/LUTs_IHP130"

# =============================================================================
# DEBUG MODE CONFIGURATION
# =============================================================================
# Set ROAR_DEBUG=1 environment variable or pass --debug command line flag to enable
# Debug mode can also be enabled programmatically by setting ROAR_DEBUG_MODE = True
# before importing other modules that use debug_print()

# Check environment variable and command line for debug flag
ROAR_DEBUG_MODE = os.environ.get("ROAR_DEBUG", "0").lower() in ("1", "true", "yes", "on")
ROAR_DEBUG_MODE = 0
if "--debug" in sys.argv:
    ROAR_DEBUG_MODE = True
    sys.argv.remove("--debug")  # Remove so Qt doesn't see it

def debug_print(*args, **kwargs):
    """Print debug messages only when ROAR_DEBUG_MODE is enabled.

    Usage: debug_print("[CATEGORY] message", ...)

    Enable debug mode by:
    - Setting environment variable: ROAR_DEBUG=1
    - Running with --debug flag: python roar_gui.py --debug
    - Setting ROAR_DEBUG_MODE = True in code
    """
    if ROAR_DEBUG_MODE:
        print(*args, **kwargs)

def set_debug_mode(enabled: bool):
    """Programmatically enable or disable debug mode."""
    global ROAR_DEBUG_MODE
    ROAR_DEBUG_MODE = enabled

def is_debug_mode() -> bool:
    """Check if debug mode is currently enabled."""
    return ROAR_DEBUG_MODE

# Legacy flags - kept for backward compatibility but now tied to ROAR_DEBUG_MODE
DEBUG = ROAR_DEBUG_MODE
DEBUG_DESIGN = ROAR_DEBUG_MODE

def format_eng(num):
    if num == 0:
        return "0"

    exp = int(np.floor(np.log10(abs(num))))
    exp3 = exp - (exp % 3)

    mant = num / 10**exp3

    if mant == int(mant):
        mant_str = f"{int(mant)}"
    else:
        mant_str = f"{mant:.2f}".rstrip('0').rstrip('.')

    if exp3 == 0:
        return mant_str
    else:
        return f"{mant_str}e{exp3}"


class EngSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that displays values using engineering notation (3-power exponents).

    It uses the project's format_eng() to render values and accepts standard float/scientific input.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow a lot of decimal precision internally so tiny values don't display as 0
        self.setDecimals(12)

    def textFromValue(self, value: float) -> str:
        try:
            # format_eng already returns '0' for zero and uses multiples-of-3 exponents
            return format_eng(float(value))
        except Exception:
            return super().textFromValue(value)

    def valueFromText(self, text: str) -> float:
        try:
            # Accept scientific input like '1e-9' as well as plain numbers
            return float(text)
        except Exception:
            # fallback to base class parsing
            return super().valueFromText(text)

    def sizeHint(self):
        """Return a sizeHint wide enough to display the engineering-formatted min/max/current values."""
        try:
            fm = self.fontMetrics()
            candidates = [format_eng(self.minimum()), format_eng(self.maximum()), format_eng(self.value())]
            # include a reasonable extra string like '-1.00e-12' to be safe
            candidates.append('-1.00e-12')
            widest = max((fm.horizontalAdvance(str(t)) for t in candidates), default=80)
            base = super().sizeHint()
            # add padding for the up/down buttons and some margin
            return QSize(max(base.width(), widest + 40), base.height())
        except Exception:
            return super().sizeHint()


class ROARTechBrowser(QWidget):
    def __init__(self, parent, lookup_window, top_level_app, tech_dict=None):
        super().__init__(parent)
        self.parent = parent
        self.lookup_window = lookup_window
        self.top_level_app = top_level_app
        self.graphing_widget = None

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # self.tree.itemClicked.connect(self.select_item)
        self.startup = True
        self.tree.itemChanged.connect(self.handle_item_changed)
        # Track pressed item to detect clicks on already-selected corners (so we can toggle selection)
        self._pressed_path = None
        self._pressed_was_selected = False
        try:
            self.tree.itemPressed.connect(self._on_item_pressed)
            self.tree.itemClicked.connect(self._on_item_clicked)
            self.tree.itemSelectionChanged.connect(self.update_all_selection_boldness)
        except Exception:
            # Some Qt builds may not expose these signals in identical ways; continue gracefully
            pass
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)

        self.tree_item_counter = 0
        self.tech_dict = tech_dict if tech_dict is not None else top_level_app.tech_dict
        self.color_map = {}
        self.path_to_item = {}

        self.pdk_item = QTreeWidgetItem(self.tree, ["PDK"])
        self.pdk_item.setFlags(self.pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.pdk_item.setCheckState(0, Qt.CheckState.Unchecked)
        self.tree.addTopLevelItem(self.pdk_item)

    @staticmethod
    def format_tech_name(name):
        """Formats a technology name to be lowercase and stripped of extra spaces."""
        return name.strip().lower()

    @staticmethod
    def create_tech_dict_from_dir(dir, pdk_name, graph_grid=None):
        tech_dict = {}
        tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir, filename)
            if os.path.isdir(f):
                model_name = filename
                ROARTechBrowser.create_devices_from_model_dir(pdk_name, model_name, f, tech_dict)
        # graph_grid.add_tech_luts(dirname=dir, pdk_name=pdk_name)
        return tech_dict

    @staticmethod
    def create_devices_from_model_dir(pdk_name, model_name, model_dir, tech_dict):
        tech_dict[pdk_name][model_name] = {}
        for filename in os.listdir(model_dir):
            length_dir = os.path.join(model_dir, filename)
            tokens = filename.split('_')
            length = tokens[-1]
            device = CIDDevice(device_name=model_name, vdd=0.0, lut_directory=length_dir, corner_list=None)
            tech_dict[pdk_name][model_name][length] = {}
            tech_dict[pdk_name][model_name][length]["device"] = device
            tech_dict[pdk_name][model_name][length]["corners"] = {}
            for corner in device.corners:
                corner_name = corner.corner_name
                tech_dict[pdk_name][model_name][length]["corners"][corner_name] = corner
        return tech_dict


    def get_checked_item_paths(self):
        checked_paths = []

        def build_path(item):
            path = []
            while item:
                path.insert(0, item.text(0))
                item = item.parent()
            return ">".join(path)

        def recurse(parent_item):
            parent_child_count = parent_item.childCount()
            for i in range(parent_child_count):
                child = parent_item.child(i)
                if child.checkState(0) == Qt.CheckState.Checked:
                    if child.childCount() == 0:
                        checked_paths.append(build_path(child))
                recurse(child)

        root = self.tree.invisibleRootItem()
        root_child_count = root.childCount()
        for i in range(root_child_count):
            recurse(root.child(i))
        return checked_paths

    def get_selected_corners(self):
        checked_items = self.tree.selectedItems()
        selected_corners = set()

        for item in checked_items:
            if not item.childCount():
                selected_corners.add(self.build_full_path(item))

        return list(selected_corners)

    def build_full_path(self, item):
        path = []
        while item:
            path.insert(0, item.text(0))
            item = item.parent()
        return ">".join(path)

    def select_item(self, item, column):
        if self.lookup_window is not None:
            # Check if app is in restore mode
            if self.top_level_app is not None and getattr(self.top_level_app, '_is_restoring_state', False):
                return
            # Check if lookup window is in updating mode
            if getattr(self.lookup_window, '_is_updating', False):
                return
            self.lookup_window.update_graph_from_tech_browser()

    def handle_item_changed(self, item, column):
        # Block signals to prevent recursive calls while we update states
        self.tree.blockSignals(True)

        try:
            check_state = item.checkState(0)
            # Propagate check state to all children
            self._set_children_check_state(item, check_state)

            # Update parent states to reflect children's check states
            self._update_parent_states(item)

        finally:
            self.tree.blockSignals(False)

        if self.startup == True:
            return 0
        # Check if app is in restore mode
        if self.top_level_app is not None and getattr(self.top_level_app, '_is_restoring_state', False):
            return 0
        # Check if lookup window is in updating mode (e.g., during state restore)
        if self.lookup_window is not None and getattr(self.lookup_window, '_is_updating', False):
            return 0
        if self.lookup_window is not None:
            self.lookup_window.update_graph_from_tech_browser()

            # ── Global tech browser sync ──
            # If this tech browser belongs to the Global master window, push
            # the checked paths to all follower (non-local) windows.
            try:
                lw = self.lookup_window
                if getattr(lw, '_is_global_browser', False) and lw.graph_grid:
                    checked_paths = self.get_checked_item_paths()
                    color_map = dict(self.color_map) if self.color_map else None
                    for other in lw.graph_grid.lookup_windows:
                        if other is not lw:
                            other.sync_from_global(checked_paths, color_map)
            except Exception:
                pass

    def _set_children_check_state(self, item, check_state):
        """Recursively set check state on all children."""
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, check_state)
            self._set_children_check_state(child, check_state)

    def _update_parent_states(self, item):
        """Update parent items' check states based on their children."""
        parent = item.parent()
        while parent is not None:
            self._update_single_parent_state(parent)
            parent = parent.parent()

    def _update_single_parent_state(self, item):
        """Update a single parent's check state based on its children."""
        if item.childCount() == 0:
            return

        checked_count = 0
        partially_checked = False
        total_count = item.childCount()

        for i in range(total_count):
            child = item.child(i)
            state = child.checkState(0)
            if state == Qt.CheckState.Checked:
                checked_count += 1
            elif state == Qt.CheckState.PartiallyChecked:
                partially_checked = True

        if partially_checked or (0 < checked_count < total_count):
            item.setCheckState(0, Qt.CheckState.PartiallyChecked)
        elif checked_count == total_count:
            item.setCheckState(0, Qt.CheckState.Checked)
        else:
            item.setCheckState(0, Qt.CheckState.Unchecked)


    def set_graphing_widget(self, graphing_widget):
        self.graphing_widget = graphing_widget

    def add_tech_luts(self, dirname=None, pdk_name=None):
        if dirname is None:
            dirname = QFileDialog.getExistingDirectory(self, "Select Directory")
            if not dirname:
                return  # User canceled

            pdk_name, ok = QInputDialog.getText(self, "Technology Process Name",
                                                "Enter name of process i.e. sky130, process_soi_22")
            if not ok or not pdk_name.strip():
                return  # User canceled or empty input

        # Build a dict that contains only the single PDK we're adding. This avoids
        # iterating all PDKs (and reparenting items) which caused devices from
        # previously added PDKs to appear under new PDK entries.
        if self.top_level_app is not None and hasattr(self.top_level_app, 'tech_dict') and pdk_name in self.top_level_app.tech_dict:
            pdk_dict = {pdk_name: self.top_level_app.tech_dict[pdk_name]}
        else:
            pdk_dict = ROARTechBrowser.create_tech_dict_from_dir(dirname, pdk_name)

        # Create top-level PDK item for the tree
        pdk_item = QTreeWidgetItem([pdk_name])
        pdk_item.setFlags(pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        pdk_item.setCheckState(0, Qt.CheckState.Unchecked)
        self.pdk_item.addChild(pdk_item)

        # Only iterate the models inside this single PDK
        models = pdk_dict.get(pdk_name, {})
        for model, model_dict in models.items():
            model_item = QTreeWidgetItem([model])
            model_item.setFlags(model_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            model_item.setCheckState(0, Qt.CheckState.Unchecked)
            pdk_item.addChild(model_item)

            for length, length_dict in model_dict.items():
                length_item = QTreeWidgetItem([length])
                length_item.setFlags(length_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                length_item.setCheckState(0, Qt.CheckState.Unchecked)
                model_item.addChild(length_item)

                for corner_name, corner_obj in length_dict.get("corners", {}).items():
                    corner_item = QTreeWidgetItem([corner_name])
                    corner_item.setFlags(corner_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    corner_item.setCheckState(0, Qt.CheckState.Unchecked)
                    length_item.addChild(corner_item)
                    full_path = self.build_full_path(corner_item)
                    self.path_to_item[full_path] = corner_item
                    self.set_item_icon(corner_item, self.get_color_for_path(full_path))

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item and not item.childCount():  # corner item
            menu = QMenu()
            set_color_action = menu.addAction("Set Color")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == set_color_action:
                selected_items = self.tree.selectedItems()
                corners = [self.build_full_path(i) for i in selected_items if not i.childCount()]

                if corners:
                    color = QColorDialog.getColor()
                    if color.isValid():
                        for path in corners:
                            self.color_map[path] = color
                        # update graph
                        self.lookup_window.update_graph_from_tech_browser()

                        # update icons
                        for path in corners:
                            if path in self.path_to_item:
                                self.set_item_icon(self.path_to_item[path], color)

    def get_color_for_path(self, path):
        if path in self.color_map:
            return self.color_map[path]
        else:
            # assign a default color
            import random
            color = QColor.fromHsv(random.randint(0, 255), 200, 200)
            self.color_map[path] = color
            return color

    def set_item_icon(self, item, color):
        pix = QPixmap(16, 16)
        pix.fill(color)
        item.setIcon(0, QIcon(pix))

    # --- Selection handling methods for bolding traces --------------------------
    def _on_item_pressed(self, item, column):
        """Track selection state before click for toggle-to-deselect."""
        try:
            self._last_pressed_item = item
        except Exception:
            self._last_pressed_item = None

    def _on_item_clicked(self, item, column):
        """Update boldness after click. Deselection handled via Ctrl+click (Qt default)."""
        try:
            # Just update boldness - let Qt handle selection/deselection via Ctrl+click
            self.update_all_selection_boldness()
        except Exception:
            pass

    def _get_all_leaf_children(self, item):
        """Recursively get all leaf (corner) items under a parent item."""
        leaves = []
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() == 0:
                # This is a leaf node (corner)
                leaves.append(child)
            else:
                # Recurse into children
                leaves.extend(self._get_all_leaf_children(child))
        return leaves

    def update_all_selection_boldness(self):
        """Walk all checked corner items and make their traces bold when selected (or parent is selected), normal when not."""
        try:
            # First, collect all selected items and their leaf children
            selected_items = self.tree.selectedItems()

            # Build a set of all leaf items that should be bold
            # (either directly selected or have a selected ancestor)
            bold_paths = set()

            for sel_item in selected_items:
                if sel_item.childCount() == 0:
                    # It's a leaf item (corner) - add it directly if checked
                    path = self.build_full_path(sel_item)
                    if sel_item.checkState(0) == Qt.CheckState.Checked:
                        bold_paths.add(path)
                else:
                    # It's a parent - add all checked leaf children
                    for leaf in self._get_all_leaf_children(sel_item):
                        if leaf.checkState(0) == Qt.CheckState.Checked:
                            path = self.build_full_path(leaf)
                            bold_paths.add(path)

            # Now iterate all checked corners and set boldness
            for path, item in list(self.path_to_item.items()):
                try:
                    is_checked = (item.checkState(0) == Qt.CheckState.Checked)
                    if not is_checked:
                        continue

                    bold = path in bold_paths
                    if self.lookup_window and hasattr(self.lookup_window, 'set_corner_boldness'):
                        try:
                            self.lookup_window.set_corner_boldness(path, bold)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
    # --------------------------------------------------------------------------------------

    def populate_from_tech_dict(self):
        """Rebuild the tree widget from the current self.tech_dict.

        This is used when a new tab is created so its tech browser shows the
        same PDK/model/length/corner structure as other tabs.
        """
        try:
            self.tree.clear()
            # Recreate a root PDK container to match previous behavior
            self.pdk_item = QTreeWidgetItem(self.tree, ["PDK"])
            self.pdk_item.setFlags(self.pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            self.pdk_item.setCheckState(0, Qt.CheckState.Unchecked)
            self.tree.addTopLevelItem(self.pdk_item)

            if not self.tech_dict:
                return

            for pdk_name, models in self.tech_dict.items():
                pdk_item = QTreeWidgetItem([pdk_name])
                pdk_item.setFlags(pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                pdk_item.setCheckState(0, Qt.CheckState.Unchecked)
                self.pdk_item.addChild(pdk_item)

                for model, model_dict in models.items():
                    model_item = QTreeWidgetItem([model])
                    model_item.setFlags(model_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    model_item.setCheckState(0, Qt.CheckState.Unchecked)
                    pdk_item.addChild(model_item)

                    for length, length_dict in model_dict.items():
                        length_item = QTreeWidgetItem([length])
                        length_item.setFlags(length_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        length_item.setCheckState(0, Qt.CheckState.Unchecked)
                        model_item.addChild(length_item)

                        for corner_name in length_dict.get("corners", {}).keys():
                            corner_item = QTreeWidgetItem([corner_name])
                            corner_item.setFlags(corner_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            corner_item.setCheckState(0, Qt.CheckState.Unchecked)
                            length_item.addChild(corner_item)
                            full_path = self.build_full_path(corner_item)
                            self.path_to_item[full_path] = corner_item
                            self.set_item_icon(corner_item, self.get_color_for_path(full_path))
        except Exception:
            pass




# ROARGraphGrid implementation moved to `roar_lookup_window.py` to reduce circular imports.
try:
    # Try package-relative import first
    from .roar_lookup_window import ROARGraphGrid
except Exception:
    try:
        from gui.roar_lookup_window import ROARGraphGrid
    except Exception:
        try:
            from roar_lookup_window import ROARGraphGrid
        except Exception:
            # Leave a minimal placeholder so the module continues to import without failing.
            class ROARGraphGrid(QWidget):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    lbl = QLabel('ROARGraphGrid not available')
                    l = QVBoxLayout(self)
                    l.addWidget(lbl)





# Import ROARPlotWidget from the lookup module (moved there to avoid circular import)
try:
    from .roar_lookup_window import ROARPlotWidget
except Exception:
    try:
        from gui.roar_lookup_window import ROARPlotWidget
    except Exception:
        try:
            from roar_lookup_window import ROARPlotWidget
        except Exception:
            ROARPlotWidget = None


class ROARHeader(QWidget):
    def __init__(self, parent=None, top_level_app=None):
        super().__init__(parent)

        # Set a taller fixed height for the header
        self.roar_teal = '#1C8091'
        banner_height = 72
        self.setFixedHeight(banner_height)  # Increased height for better spacing
        # self.setAutoFillBackground(True)  # Ensures the background color applies

        # Apply stylesheet to enforce background color
        self.setStyleSheet(f"background-color: {self.roar_teal};")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Layout adjustments
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)  # Reduced vertical padding
        layout.setSpacing(2)  # Slight spacing between buttons

        # Paths to images (Make sure ROAR_HOME is defined correctly)
        self.logo_image_path = ROAR_HOME + "/images/png/ROAR_LOGO.png"

        self.graph_calc_icon_path = ROAR_HOME + "/images/png/graph_icon_big.png"
        self.layout_icon_path = ROAR_HOME + "/images/png/layout_icon.png"

        # Verify that images exist
        self.logo_label = QLabel()
        logo_pixmap = QPixmap(self.logo_image_path)
        logo_scale = banner_height / 64
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(logo_pixmap)
            self.logo_label.setScaledContents(True)  # Ensures it resizes correctly
            self.logo_label.setFixedSize(int(181 * logo_scale),
                                         int(64 * logo_scale))  # Adjust logo size to match header
        else:
            self.logo_label.setText("Logo not found")  # Debugging fallback

        # Create buttons with icons
        self.graph_calc_icon = QPushButton()
        icon_pixmap = QPixmap(self.graph_calc_icon_path)
        if not icon_pixmap.isNull():
            icon = QIcon(icon_pixmap)
            self.graph_calc_icon.setIcon(icon)
            self.graph_calc_icon.setIconSize(icon_pixmap.rect().size())  # Ensure full-size icon
        button_scale = banner_height / 64
        self.graph_calc_icon.setFixedSize(banner_height, banner_height)  # Increased button size
        self.graph_calc_icon.setStyleSheet("""
            QPushButton {
                border: none;
                background: #1C8091;
            }
            QPushButton:hover {
                background: white;
            }
        """)

        self.layout_button = QPushButton()
        layout_pixmap = QPixmap(self.layout_icon_path)
        if not layout_pixmap.isNull():
            icon = QIcon(layout_pixmap)
            self.layout_button.setIcon(icon)
            self.layout_button.setIconSize(layout_pixmap.rect().size())  # Ensure full-size icon
        self.layout_button.setFixedSize(banner_height, banner_height)  # Increased button size
        self.layout_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: #1C8091;
            }
            QPushButton:hover {
                background: white;
            }
        """)
        self.layout_button.clicked.connect(self.on_layout_button_clicked)

        # Add widgets to layout
        layout.addWidget(self.graph_calc_icon)
        layout.addWidget(self.layout_button)
        layout.addStretch()  # Pushes everything else to the left
        layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    def on_layout_button_clicked(self):
        """Show a popup when the layout button is clicked."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Layout Integration")
        msg_box.setText("Feature Coming Soon\n\nWhat would you like to see with layout integration?")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()


class CalculatorDialog(QDialog):
    """Dialog showing available math functions for the expression/constraint editor."""

    # Define all available functions with their descriptions and examples
    FUNCTIONS = [
        # Trigonometric (radians)
        ("sin(x)", "Sine function (radians)", "sin(3.14159/2) → 1.0"),
        ("cos(x)", "Cosine function (radians)", "cos(0) → 1.0"),
        ("tan(x)", "Tangent function (radians)", "tan(3.14159/4) → 1.0"),
        ("asin(x)", "Arcsine (inverse sine), returns radians", "asin(1) → 1.5708 (π/2)"),
        ("acos(x)", "Arccosine (inverse cosine), returns radians", "acos(0) → 1.5708 (π/2)"),
        ("atan(x)", "Arctangent (inverse tangent), returns radians", "atan(1) → 0.7854 (π/4)"),

        # Trigonometric (degrees)
        ("sind(x)", "Sine function (degrees)", "sind(90) → 1.0"),
        ("cosd(x)", "Cosine function (degrees)", "cosd(0) → 1.0"),
        ("tand(x)", "Tangent function (degrees)", "tand(45) → 1.0"),
        ("asind(x)", "Arcsine, returns degrees", "asind(1) → 90"),
        ("acosd(x)", "Arccosine, returns degrees", "acosd(0) → 90"),
        ("atand(x)", "Arctangent, returns degrees", "atand(1) → 45"),

        # Exponential and Logarithmic
        ("exp(x)", "Exponential function (e^x)", "exp(1) → 2.718"),
        ("log(x)", "Natural logarithm (base e)", "log(2.718) → 1.0"),
        ("ln(x)", "Natural logarithm (same as log)", "ln(E) → 1.0"),
        ("log10(x)", "Base-10 logarithm", "log10(100) → 2.0"),

        # Power and Root
        ("sqrt(x)", "Square root", "sqrt(16) → 4.0"),
        ("x**n", "Power (x to the n)", "2**3 → 8"),
        ("abs(x)", "Absolute value", "abs(-5) → 5"),

        # Statistical
        ("min(a, b, ...)", "Minimum of values", "min(3, 1, 4) → 1"),
        ("max(a, b, ...)", "Maximum of values", "max(3, 1, 4) → 4"),
        ("sum(x)", "Sum of array values", "sum([1, 2, 3]) → 6"),
        ("mean(x)", "Mean (average) of array", "mean([1, 2, 3]) → 2.0"),
        ("std(x)", "Standard deviation of array", "std([1, 2, 3]) → 0.816"),

        # Constants
        ("pi", "Pi constant (3.14159...)", "pi → 3.14159"),
        ("E", "Euler's number (2.71828...)", "E → 2.71828"),

        # Device Lookup Syntax
        ("param:device", "Lookup device parameter", "kgm:M1 → gm/id for device M1"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculator - Math Functions Reference")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Splitter for list and details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Function list
        self.function_list = QTreeWidget()
        self.function_list.setHeaderLabels(["Function", "Description"])
        self.function_list.setColumnWidth(0, 150)
        self.function_list.setAlternatingRowColors(True)
        self.function_list.itemClicked.connect(self.on_function_selected)
        self.function_list.itemDoubleClicked.connect(self.copy_function)

        # Populate the list with categories
        categories = {
            "Trigonometric (Radians)": [],
            "Trigonometric (Degrees)": [],
            "Exponential & Logarithmic": [],
            "Power & Root": [],
            "Statistical": [],
            "Constants": [],
            "Device Lookup": [],
        }

        for func, desc, example in self.FUNCTIONS:
            if "radian" in desc.lower() or func in ["sin(x)", "cos(x)", "tan(x)", "asin(x)", "acos(x)", "atan(x)"]:
                categories["Trigonometric (Radians)"].append((func, desc, example))
            elif "degree" in desc.lower() or func.endswith("d(x)"):
                categories["Trigonometric (Degrees)"].append((func, desc, example))
            elif any(x in func.lower() for x in ["exp", "log", "ln"]):
                categories["Exponential & Logarithmic"].append((func, desc, example))
            elif any(x in func.lower() for x in ["sqrt", "**", "abs"]):
                categories["Power & Root"].append((func, desc, example))
            elif any(x in func.lower() for x in ["min", "max", "sum", "mean", "std"]):
                categories["Statistical"].append((func, desc, example))
            elif func in ["pi", "E"]:
                categories["Constants"].append((func, desc, example))
            elif ":" in func:
                categories["Device Lookup"].append((func, desc, example))

        for category, funcs in categories.items():
            if funcs:
                cat_item = QTreeWidgetItem([category, ""])
                cat_item.setExpanded(True)
                font = cat_item.font(0)
                font.setBold(True)
                cat_item.setFont(0, font)
                self.function_list.addTopLevelItem(cat_item)

                for func, desc, example in funcs:
                    func_item = QTreeWidgetItem([func, desc])
                    func_item.setData(0, Qt.ItemDataRole.UserRole, {"func": func, "desc": desc, "example": example})
                    cat_item.addChild(func_item)

        splitter.addWidget(self.function_list)

        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.func_name_label = QLabel("Select a function")
        self.func_name_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        details_layout.addWidget(self.func_name_label)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("padding: 10px; background-color: #e8f4f8; border-radius: 5px;")
        details_layout.addWidget(self.desc_label)

        example_header = QLabel("Example:")
        example_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        details_layout.addWidget(example_header)

        self.example_label = QLabel("")
        self.example_label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-radius: 5px; font-family: monospace;")
        self.example_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_layout.addWidget(self.example_label)

        details_layout.addStretch()

        # Copy button
        self.copy_button = QPushButton("📋 Copy Function to Clipboard")
        self.copy_button.clicked.connect(self.copy_function)
        self.copy_button.setEnabled(False)
        self.copy_button.setStyleSheet("padding: 10px; font-size: 14px;")
        details_layout.addWidget(self.copy_button)

        splitter.addWidget(details_widget)
        splitter.setSizes([300, 300])

        layout.addWidget(splitter)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.selected_func = None

    def on_function_selected(self, item, column):
        """Handle function selection."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.selected_func = data["func"]
            self.func_name_label.setText(data["func"])
            self.desc_label.setText(data["desc"])
            self.example_label.setText(data["example"])
            self.copy_button.setEnabled(True)
        else:
            # Category header clicked
            self.copy_button.setEnabled(False)

    def copy_function(self, item=None):
        """Copy the selected function to clipboard."""
        if self.selected_func:
            # Extract just the function name (without parameters for easier pasting)
            func_to_copy = self.selected_func
            if "(" in func_to_copy:
                func_to_copy = func_to_copy.split("(")[0] + "("
            elif ":" in func_to_copy:
                func_to_copy = ":"  # Just the lookup operator

            clipboard = QApplication.clipboard()
            clipboard.setText(func_to_copy)

            # Show feedback
            self.copy_button.setText("✓ Copied!")
            # Reset button text after 1.5 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.copy_button.setText("📋 Copy Function to Clipboard"))


class ROARApp(QMainWindow):
    def __init__(self, tech_dict=None):
        try:
            with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
                _fh.write('ROARApp.__init__ start\n')
        except Exception:
            pass
        super().__init__()

        # Set up the status bar with a QLabel for coordinates
        self.setStatusBar(QStatusBar())
        self.coord_label = QLabel("Coordinates: ")
        self.statusBar().addPermanentWidget(self.coord_label)

        # Define lookup variables
        self.lookups = ['cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'csb', 'css', 'ft', 'gds', 'gm', 'gmb',
                        'gmidft', 'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgds', 'kgm',
                        'kgmft', 'n', 'rds', 'ro', 'va', 'vds', 'vdsat', 'vgs', 'vth']
        self.lookups_units_dict = {}
        self.lookups_units_dict["cdb"] = "F"
        self.lookups_units_dict["cdd"] = "F"
        self.lookups_units_dict["cds"] = "F"
        self.lookups_units_dict["cgb"] = "F"
        self.lookups_units_dict["cgd"] = "F"
        self.lookups_units_dict["cgg"] = "F"
        self.lookups_units_dict["cgs"] = "F"
        self.lookups_units_dict["csb"] = "F"
        self.lookups_units_dict["css"] = "F"
        self.lookups_units_dict["ft"] = "Hz"
        self.lookups_units_dict["gds"] = "S"
        self.lookups_units_dict["gm"] = "A/V"
        self.lookups_units_dict["gmb"] = "A/V"
        self.lookups_units_dict["gmidft"] = "Hz/V"
        self.lookups_units_dict["gmro"] = "V/V"
        self.lookups_units_dict["ic"] = ""
        self.lookups_units_dict["iden"] = "A/m"
        self.lookups_units_dict["ids"] = "A"
        self.lookups_units_dict["kcdb"] = "F/A"
        self.lookups_units_dict["kcds"] = "F/A"
        self.lookups_units_dict["kcgd"] = "F/A"
        self.lookups_units_dict["kcgs"] = "F/A"
        self.lookups_units_dict["kgds"] = "F/A"
        self.lookups_units_dict["kgm"] = "1/V"
        self.lookups_units_dict["kgmft"] = "Hz/V"
        self.lookups_units_dict["n"] = "V/Decade"
        self.lookups_units_dict["rds"] = "Ω"
        self.lookups_units_dict["ro"] = "Ω"
        self.lookups_units_dict["va"] = "V"
        self.lookups_units_dict["vds"] = "V"
        self.lookups_units_dict["vdsat"] = "V"
        self.lookups_units_dict["vth"] = "V"

        self.tech_dict = None
        if tech_dict == None:
            self.tech_dict = {}
        else:
            self.tech_dict = tech_dict
        self.roar_teal = '#1C8091'

        # Initialize plot log state tracking
        self._plot_log_state = {}

        # Flag to prevent updates during state restore
        self._is_restoring_state = False

        # Window properties
        self.setWindowTitle("ROAR - Robust Optimal Analog Reuse")
        self.setGeometry(100, 100, 1800, 1000)

        # Create UI elements
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # No outer margins
        main_layout.setSpacing(0)  # No inner spacing between widgets
        # Add ROARHeader at the top
        self.header = ROARHeader(self, top_level_app=self)
        main_layout.addWidget(self.header)

        # Create a horizontal splitter
        splitter_h = QSplitter(Qt.Orientation.Horizontal)
        #splitter_h.setHandleWidth(1)
        self.editor_window = ROAREditorWindow(top_level_app=self)
        splitter_h.addWidget(self.editor_window)

        # Create a tab widget to hold multiple ROARGraphGrid instances (one per tab)
        from PyQt6.QtWidgets import QTabWidget, QPushButton

        self.graph_tabs = QTabWidget()
        self.graph_tabs.setMovable(True)
        self.graph_tabs.setTabsClosable(True)
        # Ensure the underlying tabBar also shows close buttons (helps when using a custom tabbar)
        try:
            self.graph_tabs.tabBar().setTabsClosable(True)
        except Exception:
            pass
        self.graph_tabs.tabCloseRequested.connect(lambda idx:
                                                  self.close_graph_tab(idx))
        # Enable right-click context menu on the tab bar for Rename/Close/Set Color
        try:
            self.graph_tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.graph_tabs.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)
        except Exception:
            pass
        # Use the custom tab bar that forwards right-clicks to ROARApp._on_tab_context_menu
        try:
            custom_bar = ROARTabBar(owner=self)
            # Make sure custom bar also exposes closable tabs if we replace the tab bar
            try:
                custom_bar.setTabsClosable(True)
            except Exception:
                pass
            self.graph_tabs.setTabBar(custom_bar)
        except Exception:
            pass

        splitter_h.addWidget(self.graph_tabs)

        # Create first default tab and ensure a '+' tab exists at the far right
        self._graph_tab_count = 0
        # Create an initial real tab
        self.create_new_graph_tab()
        # Ensure the add-tab ('+') exists as the last tab
        self.ensure_plus_tab()

        # Keep a reference to the active ROARGraphGrid for backward compatibility
        self.graph_grid = self.graph_tabs.currentWidget()

        # When the active tab changes, update self.graph_grid
        self.graph_tabs.currentChanged.connect(self._on_active_tab_changed)

        # Connect the expressions_changed signal to a slot in ROARApp
        self.editor_window.expressions_changed.connect(self.update_lookup_windows)

        # Add splitter to the layout
        main_layout.addWidget(splitter_h)

        # Set central widget
        self.setCentralWidget(central_widget)

        # ---- Dockable Python Editor + Console Panel ----
        # A QDockWidget that can be dragged to any edge of the main window.
        # Contains a vertical splitter: ROARTextEditor on top, ROARConsole below.
        from PyQt6.QtWidgets import QDockWidget

        self.python_dock = QDockWidget("Python Editor && Console", self)
        self.python_dock.setObjectName("PythonEditorConsoleDock")
        self.python_dock.setAllowedAreas(
            Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        # Allow the dock to be closed, floated, and moved
        self.python_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        # Build the inner widget: vertical splitter with editor on top, console below
        dock_splitter = QSplitter(Qt.Orientation.Vertical)
        dock_splitter.setMinimumSize(200, 150)
        dock_splitter.setChildrenCollapsible(False)

        self.python_editor = None
        if ROARTextEditor is not None:
            try:
                self.python_editor = ROARTextEditor(show_toolbar=True)
                dock_splitter.addWidget(self.python_editor)
            except Exception:
                self.python_editor = None

        self.python_console = None
        if ROARConsole is not None:
            try:
                self.python_console = ROARConsole(
                    locals_={"app": self, "__name__": "__console__"},
                )
                dock_splitter.addWidget(self.python_console)
            except Exception:
                self.python_console = None

        # Fallback label when neither widget could be created
        if self.python_editor is None and self.python_console is None:
            _placeholder = QLabel("Python console/editor unavailable. "
                                  "Install PyQt6-QScintilla to enable.")
            _placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dock_splitter.addWidget(_placeholder)

        # Give the editor ~60% and the console ~40% of the dock height
        dock_splitter.setSizes([300, 200])

        self.python_dock.setWidget(dock_splitter)
        self.python_dock.setMinimumSize(300, 200)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.python_dock)

        # Start hidden – users toggle via menu / shortcut / drag
        self.python_dock.setVisible(False)

        # Keep menu check-marks in sync whenever the dock is shown/hidden/closed
        self.python_dock.visibilityChanged.connect(self._on_dock_visibility_changed)

        # Initialize menu bar
        self.init_menu_bar()

        # Install application-wide event filter so keys are seen regardless of which widget has focus.
        # If the QApplication exists, install the filter now; otherwise log and rely on ROARApp.keyPressEvent.
        try:
            qapp = QApplication.instance()
            if qapp is not None:
                try:
                    qapp.installEventFilter(_GlobalKeyFilter(self))
                    with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
                        _fh.write('global key filter installed\n')
                except Exception:
                    pass
            else:
                try:
                    with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
                        _fh.write('QApplication.instance() returned None; event filter not installed at init\n')
                except Exception:
                    pass
        except Exception:
            pass


        sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
        predictive_28 = ROAR_CHARACTERIZATION + "/predictive_28/LUTs_1V8_mac"
        ihp130_luts = ROAR_CHARACTERIZATION + "/ihp130/LUTs_IHP130"
        #self.add_tech_luts(dir=predictive_28, pdk_name="jp28")
        #self.add_tech_luts(dir=sky130_luts, pdk_name="SKY130A")
        #self.add_tech_luts(dir=ihp130_luts, pdk_name="IHP-SG13G2")
        self.add_tech_luts_from_tech_list()
        # self.add_tech_luts(dir=predictive_28, pdk_name="predictive28_1v8")i
        #self.equation_solver = ROAREquationSolver(top_level_app=self,data_frames=[])

        if DEBUG_DESIGN:
            #design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "cs2.json")
            #design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "single_transistor_basic_variables.json")
            #design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "3d_test.json")
            #design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "common_source.json")
            design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "current_mirror_ota.json")
            self.editor_window.load_all_data(file_path=design_path, show_success_message=False)
        try:
            with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
                _fh.write('ROARApp.__init__ end\n')
        except Exception:
            pass

    def add_tech_luts_from_tech_list(self):
        import os, shlex
        path = os.path.join(ROAR_HOME or "", "tech_list.txt")
        if not os.path.isfile(path):
            # Nothing to do if list missing
            return

        with open(path, "r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                s = raw.strip()
                if not s or s.startswith('#'):
                    continue
                try:
                    parts = shlex.split(raw)
                except Exception as e:
                    print(f"Skipping malformed line {lineno} in {path}: {e}")
                    continue
                if len(parts) < 2:
                    print(f"Skipping invalid line {lineno} in {path}: expected 'pdk_name dir'")
                    continue
                pdk = parts[0]
                # Join remaining tokens to form the directory token (allow quoted paths)
                raw_dir = " ".join(parts[1:])
                # Support ${VAR} syntax by replacing with env var or module-level var (e.g., ${ROAR_HOME})
                import re
                def _replace_braced(match):
                    key = match.group(1)
                    if key in os.environ:
                        return os.environ[key]
                    # fall back to module-level variables (like ROAR_HOME)
                    val = globals().get(key)
                    return val if isinstance(val, str) else ""

                dir_after_braces = re.sub(r"\$\{([^}]+)\}", _replace_braced, raw_dir)
                # Also allow $VAR forms and expand ~
                dirpath = os.path.expanduser(os.path.expandvars(dir_after_braces))
                if not os.path.isdir(dirpath):
                    print(f"Warning: tech dir not found for {pdk}: {dirpath}")
                try:
                    self.add_tech_luts(dir=dirpath, pdk_name=pdk)
                except TypeError:
                    # older signature might expect 'dirname' kwarg
                    try:
                        self.add_tech_luts(dirname=dirpath, pdk_name=pdk)
                    except Exception as e:
                        print(f"Error adding {pdk} from line {lineno}: {e}")

    def update_lookup_windows(self, symbols):
        # Broadcast the updated expression symbols to all lookup windows on all tabs
        try:
            for i in range(self.graph_tabs.count()):
                widget = self.graph_tabs.widget(i)
                if isinstance(widget, ROARGraphGrid):
                    for window in getattr(widget, 'lookup_windows', []):
                        try:
                            window.update_expression_symbols(symbols)
                        except Exception:
                            pass
        except Exception:
            # Fall back to updating the active graph_grid if any error occurs
            try:
                for window in getattr(self.graph_grid, 'lookup_windows', []):
                    window.update_expression_symbols(symbols)
            except Exception:
                pass

    def add_tech_luts(self, dir, pdk_name):
        print("Adding technology from directory" + str(dir))
        print("PDK: " + str(pdk_name) + "\n")
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir, filename)
            if os.path.isdir(f):
                model_name = filename
                self.create_devices_from_model_dir(pdk_name=pdk_name, model_name=model_name, model_dir=f)
        # Update all tabs with the new technology LUTs
        for i in range(self.graph_tabs.count()):
            widget = self.graph_tabs.widget(i)
            if isinstance(widget, ROARGraphGrid):
                for lw in widget.lookup_windows:
                    lw.add_tech_luts(dirname=dir, pdk_name=pdk_name)
        return (self.tech_dict)

    def create_devices_from_model_dir(self, pdk_name, model_name, model_dir):
        self.tech_dict[pdk_name][model_name] = {}
        for filename in os.listdir(model_dir):
            length_dir = os.path.join(model_dir, filename)
            tokens = filename.split('_')
            length = tokens[-1]
            device = CIDDevice(device_name=model_name, vdd=0.0, lut_directory=length_dir, corner_list=None)
            self.tech_dict[pdk_name][model_name][length] = {}
            self.tech_dict[pdk_name][model_name][length]["device"] = device
            self.tech_dict[pdk_name][model_name][length]["corners"] = {}
            for corner in device.corners:
                corner_name = corner.corner_name
                self.tech_dict[pdk_name][model_name][length]["corners"][corner_name] = corner
        return (self.tech_dict)

    def init_menu_bar(self):
        """Creates the menu bar with File, Solver, Window, Export, and Help options."""
        menubar = self.menuBar()

        # ----- FILE MENU -----
        file_menu = menubar.addMenu("File")

        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)

        # App state save/load
        open_app_state_action = QAction("Open App State...", self)
        open_app_state_action.setShortcut(QKeySequence("Ctrl+O"))
        open_app_state_action.triggered.connect(self.open_app_state)

        save_app_state_action = QAction("Save App State...", self)
        save_app_state_action.setShortcut(QKeySequence("Ctrl+S"))
        save_app_state_action.triggered.connect(self.save_app_state)

        # Design-only save/load (existing functionality)
        open_design_action = QAction("Open Design...", self)
        open_design_action.triggered.connect(self.open_design_file)

        save_design_action = QAction("Save Design...", self)
        save_design_action.triggered.connect(self.save_design_file)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(open_app_state_action)
        file_menu.addAction(save_app_state_action)
        file_menu.addSeparator()
        file_menu.addAction(open_design_action)
        file_menu.addAction(save_design_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # ----- SOLVER MENU -----
        solver_menu = menubar.addMenu("Solver")

        run_solver_action = QAction("Run Solver", self)
        run_solver_action.triggered.connect(self.run_solver)
        run_solver_action.setEnabled(False)  # Disabled - feature coming soon

        stop_solver_action = QAction("Stop Solver", self)
        stop_solver_action.triggered.connect(self.stop_solver)
        stop_solver_action.setEnabled(False)  # Disabled - feature coming soon

        solver_prefs_action = QAction("Preferences", self)
        solver_prefs_action.triggered.connect(self.open_solver_preferences)
        solver_prefs_action.setEnabled(False)  # Disabled - feature coming soon

        calculator_action = QAction("Calculator", self)
        calculator_action.triggered.connect(self.show_calculator)
        calculator_action.setToolTip("Show available math functions for expressions")

        solver_menu.addAction(run_solver_action)
        solver_menu.addAction(stop_solver_action)
        solver_menu.addSeparator()
        solver_menu.addAction(calculator_action)
        solver_menu.addSeparator()

        iterative_solver_action = QAction("Iterative Solver...", self)
        iterative_solver_action.setToolTip("Open the iterative solver settings dialog")
        iterative_solver_action.triggered.connect(self._show_iterative_solver_dialog)
        solver_menu.addAction(iterative_solver_action)

        solver_menu.addSeparator()
        solver_menu.addAction(solver_prefs_action)

        # ----- WINDOW MENU -----
        window_menu = menubar.addMenu("Window")

        maximize_action = QAction("Maximize", self)
        maximize_action.triggered.connect(self.showMaximized)

        window_prefs_action = QAction("Preferences", self)
        window_prefs_action.triggered.connect(self.open_window_preferences)

        window_menu.addAction(maximize_action)
        window_menu.addAction(window_prefs_action)

        # Theme submenu: choose between Dark and Light themes
        try:
            theme_menu = window_menu.addMenu("Theme")
            theme_group = QActionGroup(self)
            # Light theme action first
            light_act = QAction("Light", self, checkable=True)
            light_act.triggered.connect(lambda: self.set_theme('light'))
            theme_group.addAction(light_act)

            theme_menu.addAction(light_act)

            # Dark theme action
            dark_act = QAction("Dark", self, checkable=True)
            dark_act.triggered.connect(lambda: self.set_theme('dark'))
            theme_group.addAction(dark_act)
            theme_menu.addAction(dark_act)


            # Make them behave like radio buttons
            try:
                theme_group.setExclusive(True)
            except Exception:
                pass

            # Initialize selection: default to light theme
            light_act.setChecked(True)
            self._current_theme = 'light'
        except Exception:
            pass

        # ---- Python Editor & Console dock toggle ----
        window_menu.addSeparator()

        self._toggle_dock_action = QAction("Python Editor && Console", self, checkable=True)
        self._toggle_dock_action.setShortcut(QKeySequence("Ctrl+`"))
        self._toggle_dock_action.setChecked(False)
        self._toggle_dock_action.triggered.connect(self._toggle_python_dock)
        window_menu.addAction(self._toggle_dock_action)

        # ----- EXPORT MENU -----
        export_menu = menubar.addMenu("Export")
        export_action = QAction("Export Data", self)
        export_action.triggered.connect(self.export_data)
        export_action.setEnabled(False)  # Disabled - feature coming soon
        export_menu.addAction(export_action)

        # ---- Export → Python Script submenu ----
        python_script_menu = export_menu.addMenu("Export to Python Script")

        export_py_file_action = QAction("Save to File…", self)
        export_py_file_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_py_file_action.triggered.connect(self.export_design_to_python_file)
        python_script_menu.addAction(export_py_file_action)

        export_py_editor_action = QAction("Send to Editor Panel", self)
        export_py_editor_action.triggered.connect(self.export_design_to_python_editor)
        python_script_menu.addAction(export_py_editor_action)

        # ----- HELP MENU -----
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    # ---- MENU ACTION CALLBACKS ----
    def new_file(self):
        """Handler for New File action."""

        QMessageBox.information(self, "New File", "New file creation is not implemented yet.")

    def open_design_file(self):
        """Opens a design file (expression editor, constraints, instances only)."""
        self.editor_window.load_all_data()

    def save_design_file(self):
        """Saves the design file (expression editor, constraints, instances only)."""
        self.editor_window.save_all_data()

    def save_app_state(self):
        """Save the complete application state to a JSON file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save App State", "", "ROAR State Files (*.roar);;JSON Files (*.json);;All Files (*.*)"
        )
        if not filename:
            return

        try:
            state = self.capture_app_state()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            QMessageBox.information(self, "Success", f"App state saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save app state:\n{str(e)}")

    def open_app_state(self):
        """Load the complete application state from a JSON file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open App State", "", "ROAR State Files (*.roar);;JSON Files (*.json);;All Files (*.*)"
        )
        if not filename:
            return

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.restore_app_state(state)
            QMessageBox.information(self, "Success", f"App state loaded from:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load app state:\n{str(e)}")

    def capture_app_state(self):
        """Capture the complete state of the application."""
        import datetime

        state = {
            'version': '1.0',
            'saved_at': datetime.datetime.now().isoformat(),
            'app_name': 'ROAR',

            # Window geometry
            'window': {
                'geometry': {
                    'x': self.x(),
                    'y': self.y(),
                    'width': self.width(),
                    'height': self.height(),
                },
                'maximized': self.isMaximized(),
            },

            # Theme
            'theme': getattr(self, '_current_theme', 'light'),

            # Console / Editor dock
            'console_panel': {
                'visible': self.python_dock.isVisible()
                    if hasattr(self, 'python_dock') else False,
                'floating': self.python_dock.isFloating()
                    if hasattr(self, 'python_dock') else False,
                'area': self.dockWidgetArea(self.python_dock).value
                    if hasattr(self, 'python_dock') else 2,  # 2 = Right
            },

            # Design editor state
            'design_editor': self._capture_design_editor_state(),

            # Graph tabs state
            'graph_tabs': self._capture_graph_tabs_state(),
        }

        return state

    def _capture_design_editor_state(self):
        """Capture the design editor state."""
        try:
            state = {
                'expression_editor': self.editor_window.expression_editor.get_table_data(),
                'constraint_editor': self.editor_window.constraint_editor.get_table_data(),
                'instance_table': self.editor_window.instance_table.get_table_data(),
            }
            # Capture iterative solver settings if available
            try:
                state['iterative_solver'] = self.editor_window.get_iterative_settings()
            except Exception:
                pass
            return state
        except Exception as e:
            debug_print(f"[SAVE STATE] Error capturing design editor state: {e}")
            return {}

    def _capture_graph_tabs_state(self):
        """Capture the state of all graph tabs."""
        tabs_state = {
            'current_tab_index': self.graph_tabs.currentIndex(),
            'tabs': [],
        }

        for i in range(self.graph_tabs.count()):
            tab_name = self.graph_tabs.tabText(i)
            # Skip the '+' tab
            if tab_name == '+':
                continue

            widget = self.graph_tabs.widget(i)
            if isinstance(widget, ROARGraphGrid):
                tab_state = {
                    'name': tab_name,
                    'windows': self._capture_graph_grid_state(widget),
                }
                tabs_state['tabs'].append(tab_state)

        return tabs_state

    def _capture_graph_grid_state(self, graph_grid):
        """Capture the state of a ROARGraphGrid (4 lookup windows)."""
        windows_state = []

        for i, window in enumerate(graph_grid.lookup_windows):
            try:
                window_state = self._capture_lookup_window_state(window)
                window_state['index'] = i
                windows_state.append(window_state)
            except Exception as e:
                debug_print(f"[SAVE STATE] Error capturing lookup window {i} state: {e}")

        return windows_state

    def _capture_lookup_window_state(self, window):
        """Capture the state of a single ROARLookupWindow."""
        state = {
            # Mode selection
            'is_device_params_mode': window.radio_device_params.isChecked(),

            # Combo box selections
            'combo_x_text': window.combo_x.currentText(),
            'combo_y_text': window.combo_y.currentText(),
            'combo_z_text': window.combo_z.currentText() if hasattr(window, 'combo_z') else '',

            # Spin box values
            'spin_x_value': window.spin_x.value(),
            'spin_y_value': window.spin_y.value(),
            'spin_z_value': window.spin_z.value() if hasattr(window, 'spin_z') else 0,

            # Checkbox states
            'checkbox_logx': window.checkbox_logx.isChecked(),
            'checkbox_logy': window.checkbox_logy.isChecked(),
            'checkbox_logz': window.checkbox_logz.isChecked() if hasattr(window, 'checkbox_logz') else False,
            'checkbox_3d': window.checkbox_3d.isChecked() if hasattr(window, 'checkbox_3d') else False,
            'checkbox_contour': window.checkbox_contour.isChecked() if hasattr(window, 'checkbox_contour') else False,
            'checkbox_legend': window.checkbox_legend.isChecked() if hasattr(window, 'checkbox_legend') else False,
            'checkbox_black_bg': window.checkbox_black_bg.isChecked() if hasattr(window, 'checkbox_black_bg') else False,

            # Lock/attachment checkboxes - capture which windows are locked to this one
            'locked_windows': self._capture_lock_state(window),

            # Tech browser state - checked items and colors
            'checked_paths': [],
            'color_map': {},
        }

        # Capture tech browser state
        try:
            if hasattr(window, 'tech_browser'):
                state['checked_paths'] = window.tech_browser.get_checked_item_paths()
                # Convert color_map values to strings for JSON serialization
                # Colors can be QColor objects or strings
                color_map_serializable = {}
                for path, color in window.tech_browser.color_map.items():
                    if hasattr(color, 'name'):  # QColor object
                        color_map_serializable[path] = color.name()
                    else:
                        color_map_serializable[path] = str(color)
                state['color_map'] = color_map_serializable
        except Exception as e:
            debug_print(f"[SAVE STATE] Error capturing tech browser state: {e}")

        # Capture markers
        try:
            state['markers'] = [
                {
                    'vertical': m['vertical'],
                    'linear_pos': m['linear_pos'],
                }
                for m in window.plot_widget.line_markers
            ]
        except Exception:
            state['markers'] = []

        return state

    def _capture_lock_state(self, window):
        """Capture which windows this window is locked to."""
        locked = []
        try:
            for i, cb in enumerate(window.setting_checkboxes):
                if cb.isChecked():
                    locked.append(i)
        except Exception:
            pass
        return locked

    def restore_app_state(self, state):
        """Restore the complete application state from a state dictionary."""
        # Create progress dialog - use NonModal so it doesn't block
        progress = QProgressDialog("Loading state...", None, 0, 100, self)
        progress.setWindowTitle("Loading State")
        progress.setWindowModality(Qt.WindowModality.NonModal)
        progress.setMinimumDuration(0)  # Show immediately
        progress.setAutoClose(False)  # We'll close it manually
        progress.setAutoReset(False)
        progress.setCancelButton(None)  # No cancel button
        progress.setMinimumWidth(300)
        progress.setValue(0)
        progress.show()
        progress.raise_()  # Bring to front
        progress.repaint()  # Force immediate repaint
        QApplication.processEvents()

        try:
            # Set global restoring flag to prevent any updates
            self._is_restoring_state = True

            # Step 1: Restore theme (5%)
            progress.setLabelText("Restoring theme...")
            progress.setValue(5)
            progress.repaint()
            QApplication.processEvents()

            theme = state.get('theme', 'light')
            self.set_theme(theme)
            # Update theme menu checkmarks
            try:
                menubar = self.menuBar()
                for action in menubar.actions():
                    menu = action.menu()
                    if menu and action.text() == "Window":
                        for sub_action in menu.actions():
                            sub_menu = sub_action.menu()
                            if sub_menu and sub_action.text() == "Theme":
                                for theme_action in sub_menu.actions():
                                    if theme_action.text().lower() == theme:
                                        theme_action.setChecked(True)
            except Exception:
                pass

            # Restore console/editor dock visibility and position
            try:
                cp = state.get('console_panel', {})
                if cp.get('floating', False):
                    self.python_dock.setFloating(True)
                else:
                    area_int = cp.get('area', 2)  # 2 = RightDockWidgetArea
                    try:
                        area = Qt.DockWidgetArea(area_int)
                    except Exception:
                        area = Qt.DockWidgetArea.RightDockWidgetArea
                    self.addDockWidget(area, self.python_dock)
                self.python_dock.setVisible(cp.get('visible', False))
            except Exception:
                pass

            # Step 2: Restore design editor (15%)
            progress.setLabelText("Restoring design editor...")
            progress.setValue(15)
            progress.repaint()
            QApplication.processEvents()

            design_state = state.get('design_editor', {})
            if design_state:
                self._restore_design_editor_state(design_state)

            # Step 3: Restore graph tabs (20-90%)
            progress.setLabelText("Restoring graph tabs...")
            progress.setValue(20)
            progress.repaint()
            QApplication.processEvents()

            tabs_state = state.get('graph_tabs', {})
            if tabs_state:
                self._restore_graph_tabs_state(tabs_state, progress)

            # Step 4: Restore window geometry (95%)
            progress.setLabelText("Restoring window layout...")
            progress.setValue(95)
            progress.repaint()
            QApplication.processEvents()

            window_state = state.get('window', {})
            if window_state:
                geom = window_state.get('geometry', {})
                if geom:
                    self.setGeometry(
                        geom.get('x', 100),
                        geom.get('y', 100),
                        geom.get('width', 1200),
                        geom.get('height', 800)
                    )
                if window_state.get('maximized', False):
                    self.showMaximized()

            # Complete (100%)
            progress.setLabelText("Complete!")
            progress.setValue(100)
            progress.repaint()
            QApplication.processEvents()

            # Close the progress dialog
            progress.close()

            # Clear status message
            self.statusBar().showMessage("App state restored.", 3000)

            # Clear global restoring flag
            self._is_restoring_state = False

        except Exception as e:
            progress.close()
            debug_print(f"[RESTORE STATE] Error: {e}")
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage("Error restoring app state.", 5000)
            self._is_restoring_state = False
            raise

    def _restore_design_editor_state(self, state):
        """Restore the design editor state."""
        try:
            if 'expression_editor' in state:
                self.editor_window.expression_editor.load_table_data(state['expression_editor'])
            if 'constraint_editor' in state:
                self.editor_window.constraint_editor.load_table_data(state['constraint_editor'])
            if 'instance_table' in state:
                self.editor_window.instance_table.load_table_data(state['instance_table'])
            # Restore iterative solver settings
            iter_data = state.get('iterative_solver', {})
            if iter_data:
                try:
                    ew = self.editor_window
                    dlg = ew._get_or_create_iterative_dialog()
                    dlg.set_settings(iter_data)
                except Exception as e2:
                    debug_print(f"[RESTORE STATE] Error restoring iterative solver settings: {e2}")
            # Don't emit signal here - let _restore_graph_grid_state handle updates
            # This prevents double-updating when restoring full app state
        except Exception as e:
            debug_print(f"[RESTORE STATE] Error restoring design editor: {e}")

    def _restore_graph_tabs_state(self, state, progress=None):
        """Restore the state of all graph tabs."""
        tabs = state.get('tabs', [])
        if not tabs:
            return

        if progress:
            progress.setLabelText("Closing existing tabs...")
        QApplication.processEvents()

        # Block signals on graph_tabs to prevent callbacks during tab removal
        self.graph_tabs.blockSignals(True)

        try:
            # Close all existing tabs except the '+' tab
            # Use a safer approach: collect indices to remove, then remove from end
            tabs_to_remove = []
            for i in range(self.graph_tabs.count()):
                if self.graph_tabs.tabText(i) != '+':
                    tabs_to_remove.append(i)

            # Remove from end to start to avoid index shifting issues
            for i in reversed(tabs_to_remove):
                self.graph_tabs.removeTab(i)
                QApplication.processEvents()
        finally:
            self.graph_tabs.blockSignals(False)

        QApplication.processEvents()

        # Calculate progress range for tabs (20% to 90% = 70% range)
        progress_start = 20
        progress_range = 70
        total_tabs = len(tabs)

        # Create tabs for each saved state
        for tab_index, tab_state in enumerate(tabs):
            # Calculate progress for this tab
            if progress and total_tabs > 0:
                tab_progress = progress_start + int((tab_index / total_tabs) * progress_range)
                progress.setLabelText(f"Restoring tab {tab_index + 1} of {total_tabs}...")
                progress.setValue(tab_progress)
                progress.repaint()
            QApplication.processEvents()

            tab_name = tab_state.get('name', f'Graph {tab_index + 1}')

            if tab_index == 0 and self.graph_tabs.count() > 0:
                # Check if first tab exists and is not '+'
                first_tab_is_plus = self.graph_tabs.tabText(0) == '+'
                if first_tab_is_plus:
                    # Create new tab
                    self.create_new_graph_tab()
                    widget = self.graph_tabs.widget(0)  # New tab is at index 0
                else:
                    widget = self.graph_tabs.widget(0)

                if isinstance(widget, ROARGraphGrid):
                    self.graph_tabs.setTabText(0, tab_name)
            else:
                # Create new tab
                self.create_new_graph_tab()
                # The new tab is inserted before the '+' tab
                new_tab_index = self.graph_tabs.count() - 2  # -2 to skip '+' tab
                if new_tab_index >= 0:
                    self.graph_tabs.setTabText(new_tab_index, tab_name)
                    widget = self.graph_tabs.widget(new_tab_index)
                else:
                    widget = None

            if isinstance(widget, ROARGraphGrid):
                windows_state = tab_state.get('windows', [])
                self._restore_graph_grid_state(widget, windows_state, progress, tab_index, total_tabs, progress_start, progress_range)

        # Restore current tab index
        current_idx = state.get('current_tab_index', 0)
        if 0 <= current_idx < self.graph_tabs.count():
            self.graph_tabs.setCurrentIndex(current_idx)

        # Ensure '+' tab exists
        self.ensure_plus_tab()

    def _restore_graph_grid_state(self, graph_grid, windows_state, progress=None, tab_index=0, total_tabs=1, progress_start=20, progress_range=70):
        """Restore the state of a ROARGraphGrid."""
        num_windows = len(windows_state)

        # Single pass: restore settings then immediately update graph for each window
        for i, window_state in enumerate(windows_state):
            idx = window_state.get('index', 0)
            if 0 <= idx < len(graph_grid.lookup_windows):
                window = graph_grid.lookup_windows[idx]

                # Update progress - show which window we're restoring
                if progress and total_tabs > 0 and num_windows > 0:
                    # Calculate sub-progress: each window gets equal portion within this tab's range
                    tab_portion = progress_range / total_tabs
                    win_portion = tab_portion / num_windows
                    win_progress = progress_start + int(tab_index * tab_portion + i * win_portion)
                    progress.setLabelText(f"Tab {tab_index + 1}/{total_tabs}: Restoring window {i + 1}/{num_windows}...")
                    progress.setValue(win_progress)
                    progress.repaint()
                QApplication.processEvents()

                # Restore window settings
                self._restore_lookup_window_state(window, window_state)

                # Update progress - show we're updating the graph
                if progress and total_tabs > 0 and num_windows > 0:
                    tab_portion = progress_range / total_tabs
                    win_portion = tab_portion / num_windows
                    win_progress = progress_start + int(tab_index * tab_portion + (i + 0.5) * win_portion)
                    progress.setLabelText(f"Tab {tab_index + 1}/{total_tabs}: Plotting window {i + 1}/{num_windows}...")
                    progress.setValue(win_progress)
                    progress.repaint()
                QApplication.processEvents()

                # Update the graph immediately after restoring settings
                # Use skip_post_processing=True to speed up restore
                try:
                    window.update_graph_from_tech_browser(skip_post_processing=True)
                except Exception as e:
                    debug_print(f"Error updating graph: {e}")
                QApplication.processEvents()

    def _restore_lookup_window_state(self, window, state):
        """Restore the state of a single ROARLookupWindow."""
        try:
            # Temporarily disable updates
            window._is_updating = True

            # Block signals on all widgets to prevent cascading updates
            widgets_to_block = [
                window.radio_device_params,
                window.radio_design_eq,
                window.combo_x,
                window.combo_y,
                window.spin_x,
                window.spin_y,
                window.checkbox_logx,
                window.checkbox_logy,
            ]
            # Add optional widgets if they exist
            for attr in ['combo_z', 'spin_z', 'checkbox_logz', 'checkbox_3d',
                         'checkbox_contour', 'checkbox_black_bg']:
                if hasattr(window, attr):
                    widgets_to_block.append(getattr(window, attr))

            # Block all signals
            for widget in widgets_to_block:
                try:
                    widget.blockSignals(True)
                except Exception:
                    pass

            # Restore mode selection and explicitly set the mode variable
            if state.get('is_device_params_mode', True):
                window.radio_device_params.setChecked(True)
                window.is_device_params_mode = True
            else:
                window.radio_design_eq.setChecked(True)
                window.is_device_params_mode = False

            # Update combo box items to match the mode (before restoring selections)
            window.update_combobox_items()

            # Restore combo boxes
            window.combo_x.setCurrentText(state.get('combo_x_text', ''))
            window.combo_y.setCurrentText(state.get('combo_y_text', ''))
            if hasattr(window, 'combo_z'):
                window.combo_z.setCurrentText(state.get('combo_z_text', ''))

            # Restore spin boxes
            window.spin_x.setValue(state.get('spin_x_value', 0))
            window.spin_y.setValue(state.get('spin_y_value', 0))
            if hasattr(window, 'spin_z'):
                window.spin_z.setValue(state.get('spin_z_value', 0))

            # Restore checkboxes
            window.checkbox_logx.setChecked(state.get('checkbox_logx', False))
            window.checkbox_logy.setChecked(state.get('checkbox_logy', False))
            if hasattr(window, 'checkbox_logz'):
                window.checkbox_logz.setChecked(state.get('checkbox_logz', False))
            if hasattr(window, 'checkbox_3d'):
                window.checkbox_3d.setChecked(state.get('checkbox_3d', False))
            if hasattr(window, 'checkbox_contour'):
                window.checkbox_contour.setChecked(state.get('checkbox_contour', False))
            if hasattr(window, 'checkbox_black_bg'):
                window.checkbox_black_bg.setChecked(state.get('checkbox_black_bg', False))

            # Restore tech browser checked items (this method already blocks signals internally)
            if 'checked_paths' in state and hasattr(window, 'restore_tech_browser_checks'):
                window.restore_tech_browser_checks(state['checked_paths'])

            # Restore tech browser color map
            if 'color_map' in state and hasattr(window, 'tech_browser'):
                window.tech_browser.color_map = dict(state['color_map'])
                # Update icons
                for path, color in window.tech_browser.color_map.items():
                    if path in window.tech_browser.path_to_item:
                        item = window.tech_browser.path_to_item[path]
                        if item.childCount() == 0:
                            try:
                                from PyQt6.QtGui import QPixmap, QIcon
                                pixmap = QPixmap(16, 16)
                                pixmap.fill(QColor(color))
                                item.setIcon(0, QIcon(pixmap))
                            except Exception:
                                pass

            # Unblock all signals
            for widget in widgets_to_block:
                try:
                    widget.blockSignals(False)
                except Exception:
                    pass

            # Restore lock states (after all windows are created)
            # Block setting checkbox signals too
            for cb in window.setting_checkboxes:
                try:
                    cb.blockSignals(True)
                except Exception:
                    pass

            locked_windows = state.get('locked_windows', [])
            for i in locked_windows:
                if 0 <= i < len(window.setting_checkboxes):
                    window.setting_checkboxes[i].setChecked(True)

            for cb in window.setting_checkboxes:
                try:
                    cb.blockSignals(False)
                except Exception:
                    pass

            # Re-enable updates
            window._is_updating = False

            # Restore markers (don't sync to avoid cascading)
            markers = state.get('markers', [])
            for marker_state in markers:
                try:
                    linear_pos = marker_state.get('linear_pos')
                    if marker_state.get('vertical', True):
                        window.plot_widget.add_vertical_marker(linear_pos=linear_pos, sync=False)
                    else:
                        window.plot_widget.add_horizontal_marker(linear_pos=linear_pos, sync=False)
                except Exception:
                    pass

        except Exception as e:
            debug_print(f"[RESTORE STATE] Error restoring lookup window: {e}")
            import traceback
            traceback.print_exc()
            # Ensure _is_updating is reset even on error
            try:
                window._is_updating = False
            except Exception:
                pass

    # ---- Python Editor & Console Dock Controls ----

    def _toggle_python_dock(self, checked=None):
        """Toggle visibility of the Python Editor & Console dock widget.

        Keyboard shortcut: ``Ctrl+` `` (set in menu bar).
        """
        if checked is None:
            checked = not self.python_dock.isVisible()
        self.python_dock.setVisible(checked)

    def _on_dock_visibility_changed(self, visible):
        """Slot connected to ``python_dock.visibilityChanged`` so the menu
        check-mark stays in sync when the user closes the dock via its
        title-bar button or drags it around."""
        try:
            self._toggle_dock_action.setChecked(visible)
        except Exception:
            pass

    def show_console_panel(self, tab_name: str | None = None):
        """Show the Python Editor & Console dock.

        The *tab_name* parameter is accepted for backward compatibility but
        is ignored — the editor and console are always shown together now.
        """
        self.python_dock.setVisible(True)
        self.python_dock.raise_()

    def hide_console_panel(self):
        """Hide the Python Editor & Console dock."""
        self.python_dock.setVisible(False)

    def run_solver(self):
        """Placeholder function for running solver."""
        QMessageBox.information(self, "Run Solver", "Solver started.")

    def stop_solver(self):
        """Placeholder function for stopping solver."""
        QMessageBox.warning(self, "Stop Solver", "Solver stopped.")

    def _show_iterative_solver_dialog(self):
        """Open the iterative solver settings dialog via the design editor."""
        if hasattr(self, 'editor_window') and self.editor_window is not None:
            self.editor_window.show_iterative_solver_dialog()

    def show_calculator(self):
        """Show the Calculator dialog with available math functions."""
        dialog = CalculatorDialog(self)
        dialog.exec()

    def open_solver_preferences(self):
        """Opens solver preferences."""
        QMessageBox.information(self, "Preferences", "Solver preferences dialog is not implemented yet.")

    def open_window_preferences(self):
        """Opens window preferences."""
        QMessageBox.information(self, "Preferences", "Window preferences dialog is not implemented yet.")

    def export_data(self):
        """Handles data export."""
        QMessageBox.information(self, "Export", "Data export feature is not implemented yet.")

    # ---- Python Script export helpers ----

    def _generate_design_python_script(self) -> str | None:
        """Collect design editor state and generate a Python script string.

        Returns ``None`` (and shows an error dialog) when the required export
        function or design data is unavailable.
        """
        # Lazy import – keeps module-level import block unchanged
        _export_fn = None
        try:
            from roar_console import export_design_to_python as _fn
            _export_fn = _fn
        except Exception:
            pass
        if _export_fn is None:
            try:
                from gui.roar_console import export_design_to_python as _fn
                _export_fn = _fn
            except Exception:
                pass
        if _export_fn is None:
            QMessageBox.critical(
                self, "Export Error",
                "Could not import the export function.\n"
                "Make sure roar_console.py is present and PyQt6-QScintilla is installed.")
            return None

        try:
            expressions, constraints = \
                self.editor_window.get_expressions_and_constraints()
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to read expressions/constraints:\n{exc}")
            return None

        try:
            instances = self.editor_window.instance_table.get_table_data()
        except Exception:
            instances = []

        try:
            device_corners = self.editor_window.get_device_corners()
        except Exception:
            device_corners = {}

        try:
            script = _export_fn(
                expressions=expressions,
                constraints=constraints,
                instances=instances,
                device_corners=device_corners,
            )
            return script
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Error",
                f"Script generation failed:\n{exc}")
            return None

    def export_design_to_python_file(self):
        """Export the current design to a ``.py`` file (Export → Python Script → Save to File)."""
        script = self._generate_design_python_script()
        if script is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Python Script", "",
            "Python Files (*.py);;All Files (*)")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(script)
            QMessageBox.information(
                self, "Export Successful",
                f"Design exported to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to write file:\n{exc}")

    def export_design_to_python_editor(self):
        """Export the current design into the built-in Python Editor panel
        (Export → Python Script → Send to Editor Panel)."""
        script = self._generate_design_python_script()
        if script is None:
            return

        if self.python_editor is None:
            QMessageBox.warning(
                self, "Editor Unavailable",
                "The Python Editor panel is not available.\n"
                "Install PyQt6-QScintilla to enable it.")
            return

        self.python_editor.set_text(script)
        # Make sure the panel is visible and switched to the Editor tab
        self.show_console_panel(tab_name="Editor")

    def show_about_dialog(self):
        """Displays an About dialog."""
        QMessageBox.about(self, "About ROAR", "ROAR - Robust Optimal Analog Reuse\nVersion 1.0\n© 2026 ROAR Inc.")

    def set_theme(self, theme_name: str):
        """Apply 'dark' or 'light' theme to the application.

        For 'light', use the default PyQt6 theme. For 'dark', use qdarktheme if available, else manual palette.
        """
        try:
            qapp = QApplication.instance() or QApplication(sys.argv)
            # Use qdarktheme for dark theme only
            try:
                import qdarktheme
                if theme_name == 'dark':
                    qdarktheme.setup_theme('dark')
                    self._current_theme = theme_name
                    return
            except Exception:
                pass

            # For light or fallback, set standard palette
            qapp.setPalette(QApplication.style().standardPalette())
            qapp.setStyleSheet("")
            self._current_theme = theme_name

            # Manual dark palette as last resort if qdarktheme failed for dark
            if theme_name == 'dark':
                pal = QPalette()
                pal.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
                pal.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
                pal.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
                pal.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
                pal.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
                pal.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
                pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
                pal.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
                pal.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
                pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
                qapp.setPalette(pal)
                qapp.setStyleSheet("")
        except Exception:
            pass

    def keyPressEvent(self, event):
        """Handle global hotkeys directly on the main window: L (toggle both log axes),
        X (toggle log X), Y (toggle log Y), F (auto-fit).
        This method is a reliable fallback when QShortcut/QAction registration fails
        or when focus handling prevents application-wide shortcuts from firing.
        """
        # Debug trace: record every keyPressEvent seen by the main window for diagnosis
        try:
            try:
                txt = event.text() or ''
            except Exception:
                txt = ''
            try:
                with open('/tmp/roar_keypress_event.log', 'a', encoding='utf-8') as _fh:
                    _fh.write(f"ROARApp.keyPressEvent: text={repr(txt)} key={event.key()} mods={int(event.modifiers())}\n")
            except Exception:
                pass
        except Exception:
            pass
        try:
            # Prefer event.text() so lowercase letters work without Shift
            try:
                ch = event.text().lower()
            except Exception:
                ch = None
            key = event.key()
            if ch == 'x':
                try:
                    self._shortcut_toggle_log_x()
                    event.accept()
                    return
                except Exception:
                    pass
            if ch == 'y':
                try:
                    self._shortcut_toggle_log_y()
                    event.accept()
                    return
                except Exception:
                    pass
            if ch == 'f':
                try:
                    self._shortcut_auto_fit()
                    event.accept()
                    return
                except Exception:
                    pass
            if ch == 'v' or key == Qt.Key.Key_V:
                try:
                    self._shortcut_add_vertical_marker()
                    event.accept()
                    return
                except Exception:
                    pass
            if ch == 'h' or key == Qt.Key.Key_H:
                try:
                    self._shortcut_add_horizontal_marker()
                    event.accept()
                    return
                except Exception:
                    pass
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Escape):
                # In 3-D mode, clear all point markers
                try:
                    gl_w = self._find_active_3d_widget()
                    if gl_w is not None and hasattr(gl_w, 'clear_all_3d_markers'):
                        gl_w.clear_all_3d_markers()
                        gl_w.update()
                except Exception:
                    pass
                if key == Qt.Key.Key_Escape:
                    pass  # let Escape propagate for other handlers
                else:
                    event.accept()
                    return
            # fallback to raw key constant
            if key == Qt.Key.Key_L:
                try:
                    self._shortcut_toggle_log_both()
                    event.accept()
                    return
                except Exception:
                    pass
            if key == Qt.Key.Key_X:
                try:
                    self._shortcut_toggle_log_x()
                    event.accept()
                    return
                except Exception:
                    pass
            if key == Qt.Key.Key_Y:
                try:
                    self._shortcut_toggle_log_y()
                    event.accept()
                    return
                except Exception:
                    pass
            if key == Qt.Key.Key_F:
                try:
                    self._shortcut_auto_fit()
                    event.accept()
                    return
                except Exception:
                    pass
            if key == Qt.Key.Key_V:
                try:
                    self._shortcut_add_vertical_marker()
                    event.accept()
                    return
                except Exception:
                    pass
            if key == Qt.Key.Key_H:
                try:
                    self._shortcut_add_horizontal_marker()
                    event.accept()
                    return
                except Exception:
                    pass
        except Exception:
            pass
        # fallback to base class for other keys
        try:
            super().keyPressEvent(event)
        except Exception:
            pass

    # ----------------- Tab management for graph grids -----------------
    def create_new_graph_tab(self):
        """Create a new tab containing its own ROARGraphGrid."""
        try:
            self._graph_tab_count += 1
            tab_name = f"Graph {self._graph_tab_count}"
            grid = ROARGraphGrid(parent=self, top_level_app=self)
            # If a '+' tab exists at the end, insert before it so '+' stays last
            plus_exists = (self.graph_tabs.count() > 0 and self.graph_tabs.tabText(self.graph_tabs.count() - 1) == '+')
            insert_pos = self.graph_tabs.count() - 1 if plus_exists else self.graph_tabs.count()
            self.graph_tabs.insertTab(insert_pos, grid, tab_name)
            # Make the new tab the current tab
            self.graph_tabs.setCurrentIndex(insert_pos)
            # Update active reference
            self.graph_grid = grid
            # Ensure '+' tab remains at the end
            self.ensure_plus_tab()

            # Populate the new tab's lookup windows from the app's tech_dict
            grid.populate_from_app()

            # Robust fallback: ensure there's at least one PlotWidget in the tab so
            # application-level shortcuts have something to operate on. This helps
            # when the real ROARGraphGrid/ROARLookupWindow couldn't be imported and
            # a lightweight placeholder was used instead.
            try:
                existing = [p for p in grid.findChildren(pg.PlotWidget)]
                if not existing:
                    try:
                        pw = pg.PlotWidget()
                        # mark initial log flags
                        setattr(pw, '_log_x', False)
                        setattr(pw, '_log_y', False)
                        # help the shortcut code find context
                        try:
                            setattr(pw, 'parent_lookup_window', grid)
                        except Exception:
                            pass
                        try:
                            pi = pw.getPlotItem()
                            setattr(pw, 'plotItem', pi)
                        except Exception:
                            pass
                        # attach to grid's layout or create one
                        if isinstance(grid.layout(), QVBoxLayout) or hasattr(grid, 'layout'):
                            try:
                                l = grid.layout()
                                if l is None:
                                    l = QVBoxLayout(grid)
                                    grid.setLayout(l)
                                l.addWidget(pw)
                            except Exception:
                                try:
                                    l = QVBoxLayout()
                                    l.addWidget(pw)
                                    grid.setLayout(l)
                                except Exception:
                                    pass
                        else:
                            try:
                                l = QVBoxLayout(grid)
                                l.addWidget(pw)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            return grid
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create graph tab: {e}")
            return None

    def close_graph_tab(self, index: int):
        """Close the tab at `index`. Always ensure at least one tab remains."""
        try:
            # Validate index
            if index < 0 or index >= self.graph_tabs.count():
                return
            # Do not allow closing the '+' add-tab
            if self.graph_tabs.tabText(index) == '+':
                return

            # Remove the tab and its widget while blocking tab signals to avoid
            # the '+' activation handler creating a new tab mid-rearrangement.
            widget = self.graph_tabs.widget(index)
            try:
                try:
                    self.graph_tabs.currentChanged.disconnect(self._on_active_tab_changed)
                except Exception:
                    # if already disconnected, ignore
                    pass
                self.graph_tabs.removeTab(index)
                try:
                    widget.deleteLater()
                except Exception:
                    pass

                # Ensure '+' placeholder remains at the end
                self.ensure_plus_tab()

                # Find first real tab and set it current; if none exist, create one
                real_idx = None
                for i in range(self.graph_tabs.count()):
                    if self.graph_tabs.tabText(i) != '+':
                        real_idx = i
                        break
                if real_idx is None:
                    # No real tabs: create one
                    self.create_new_graph_tab()
                else:
                    # Choose a reasonable tab to select (prefer left neighbor of closed index)
                    preferred = max(0, min(real_idx, index - 1))
                    found = None
                    for delta in range(0, self.graph_tabs.count()):
                        for cand in (preferred - delta, preferred + delta):
                            if 0 <= cand < self.graph_tabs.count() and self.graph_tabs.tabText(cand) != '+':
                                found = cand
                                break
                        if found is not None:
                            break
                    if found is not None:
                        self.graph_tabs.setCurrentIndex(found)
                # Update active reference to the now-current widget
                cur = self.graph_tabs.currentWidget()
                self.graph_grid = cur
            finally:
                try:
                    # Reconnect the handler; ignore if it fails
                    self.graph_tabs.currentChanged.connect(self._on_active_tab_changed)
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to close tab: {e}")

    def _on_tab_context_menu(self, pos):
        """Show context menu for tab operations: Rename, Close, Set Color."""
        try:
            tab_bar = self.graph_tabs.tabBar()
            idx = tab_bar.tabAt(pos)
            if idx < 0:
                return
            # Do not allow context menu on the '+' add-tab
            if self.graph_tabs.tabText(idx) == '+':
                return
            menu = QMenu()
            rename_act = menu.addAction("Rename")
            close_act = menu.addAction("Close")
            color_act = menu.addAction("Set Color")
            action = menu.exec(tab_bar.mapToGlobal(pos))
            if action == rename_act:
                text, ok = QInputDialog.getText(self, "Rename Tab", "New name:", text=self.graph_tabs.tabText(idx))
                if ok and text:
                    self.graph_tabs.setTabText(idx, text)
            elif action == close_act:
                # Close the specified tab (guarded inside close_graph_tab)
                self.close_graph_tab(idx)
            elif action == color_act:
                color = QColorDialog.getColor()
                if color.isValid():
                    # show a colored icon on the tab
                    pix = QPixmap(16, 16)
                    pix.fill(color)
                    self.graph_tabs.setTabIcon(idx, QIcon(pix))
        except Exception:
            pass

    def _on_active_tab_changed(self, index: int):
        """Update active graph_grid reference when the selected tab changes."""
        try:
            # If the user activated the special '+' tab, create a new tab and switch to it
            if index >= 0 and self.graph_tabs.tabText(index) == '+':
                new_grid = self.create_new_graph_tab()
                # create_new_graph_tab sets current and graph_grid already
                return
            widget = self.graph_tabs.widget(index)
            self.graph_grid = widget
        except Exception:
            self.graph_grid = None

    def ensure_plus_tab(self):
        """Ensure there's a '+' tab at the end of the tab bar. If one exists elsewhere, normalize it to the end."""
        try:
            count = self.graph_tabs.count()
            if count == 0:
                # No tabs: just add a '+' placeholder
                placeholder = QWidget()
                placeholder.setEnabled(False)
                self.graph_tabs.addTab(placeholder, '+')
                # Remove the close ('x') button for the '+' tab
                try:
                    tab_bar = self.graph_tabs.tabBar()
                    last = self.graph_tabs.count() - 1
                    tab_bar.setTabButton(last, QTabBar.ButtonPosition.RightSide, None)
                except Exception:
                    pass
                return
            # If last tab is already '+', we're done
            if self.graph_tabs.tabText(count - 1) == '+':
                return
            # If '+' exists elsewhere, remove it
            plus_index = None
            for i in range(count):
                if self.graph_tabs.tabText(i) == '+':
                    plus_index = i
                    break
            if plus_index is not None:
                w = self.graph_tabs.widget(plus_index)
                self.graph_tabs.removeTab(plus_index)
                try:
                    w.deleteLater()
                except Exception:
                    pass
            # Add a disabled placeholder tab labeled '+' at the end
            placeholder = QWidget()
            placeholder.setEnabled(False)
            self.graph_tabs.addTab(placeholder, '+')
            # Remove the close ('x') button for the '+' tab
            try:
                tab_bar = self.graph_tabs.tabBar()
                last = self.graph_tabs.count() - 1
                tab_bar.setTabButton(last, QTabBar.ButtonPosition.RightSide, None)
            except Exception:
                pass
        except Exception:
            pass

    def _apply_to_plotwidgets(self, handler):
        """Find PlotWidget-like objects in the active graph tab and call handler(pw).

        This looks for:
        - plot_widget attribute on each lookup window (ROARLookupWindow.plot_widget)
        - direct pg.PlotWidget descendants via findChildren
        - wrappers exposing getPlotItem() (duck-typing)
        """
        try:
            grid = getattr(self, 'graph_grid', None)
            if grid is None:
                return

            found = []

            # Direct: if graph_grid exposes lookup_windows (ROARGraphGrid does)
            try:
                for lw in getattr(grid, 'lookup_windows', []) or []:
                    try:
                        # common attribute used by ROARLookupWindow
                        pw = getattr(lw, 'plot_widget', None)
                        if pw is not None and pw not in found:
                            found.append(pw)
                            continue
                    except Exception:
                        pass

                    # fallback: discover any PlotWidget children under the lookup window
                    try:
                        found.extend([p for p in lw.findChildren(pg.PlotWidget) if p not in found])
                    except Exception:
                        pass

            except Exception:
                pass

            # Also scan the grid itself for PlotWidget descendants
            try:
                found.extend([p for p in grid.findChildren(pg.PlotWidget) if p not in found])
            except Exception:
                pass

            # As a final fallback, walk QWidget descendants and accept wrappers exposing getPlotItem()
            try:
                for w in grid.findChildren(QWidget):
                    try:
                        if w in found:
                            continue
                        if hasattr(w, 'getPlotItem') and callable(getattr(w, 'getPlotItem')):
                            found.append(w)
                    except Exception:
                        pass
            except Exception:
                pass

            # Build a small proxy that exposes the minimal plot API the handlers expect.
            class _PlotProxy:
                def __init__(self, src):
                    self._src = src
                    try:
                        self._pi = self.getPlotItem()
                        self._pi_id = id(self._pi) if self._pi is not None else None
                    except Exception:
                        self._pi = None
                        self._pi_id = None

                def getPlotItem(self):
                    # Prefer direct PlotItem access
                    try:
                        if hasattr(self._src, 'getPlotItem') and callable(getattr(self._src, 'getPlotItem')):
                            return self._src.getPlotItem()
                    except Exception:
                        pass
                    try:
                        # Some wrappers expose .plotItem
                        if hasattr(self._src, 'plotItem'):
                            return getattr(self._src, 'plotItem')
                    except Exception:
                        pass
                    try:
                        # If it's already a PlotItem, return it
                        import pyqtgraph as _pg
                        if isinstance(self._src, _pg.PlotItem):
                            return self._src
                    except Exception:
                        pass
                    return None

                def setLogMode(self, x=False, y=False):
                    # Try to call setLogMode on the source or on the PlotItem
                    try:
                        if hasattr(self._src, 'setLogMode') and callable(self._src.setLogMode):
                            self._src.setLogMode(x=x, y=y)
                            return
                    except Exception:
                        pass
                    try:
                        pi = self.getPlotItem()
                        if pi is not None and hasattr(pi, 'setLogMode') and callable(pi.setLogMode):
                            pi.setLogMode(x=x, y=y)
                            return
                    except Exception:
                        pass

                def getViewBox(self):
                    try:
                        if hasattr(self._src, 'getViewBox') and callable(self._src.getViewBox):
                            return self._src.getViewBox()
                    except Exception:
                        pass
                    try:
                        pi = self.getPlotItem()
                        if pi is not None and hasattr(pi, 'getViewBox') and callable(pi.getViewBox):
                            return pi.getViewBox()
                    except Exception:
                        pass
                    return None

                def enableAutoRange(self):
                    try:
                        if hasattr(self._src, 'enableAutoRange') and callable(self._src.enableAutoRange):
                            return self._src.enableAutoRange()
                    except Exception:
                        pass
                    try:
                        pi = self.getPlotItem()
                        if pi is not None and hasattr(pi, 'enableAutoRange') and callable(pi.enableAutoRange):
                            return pi.enableAutoRange()
                    except Exception:
                        pass
                    return None

                def add_vertical_marker(self):
                    try:
                        if hasattr(self._src, 'add_vertical_marker') and callable(self._src.add_vertical_marker):
                            return self._src.add_vertical_marker()
                    except Exception:
                        pass

                def add_horizontal_marker(self):
                    try:
                        if hasattr(self._src, 'add_horizontal_marker') and callable(self._src.add_horizontal_marker):
                            return self._src.add_horizontal_marker()
                    except Exception:
                        pass
                def __repr__(self):
                    return f"_PlotProxy({type(self._src)})"

            for pw in found:
                try:
                    proxy = _PlotProxy(pw)
                    handler(proxy)
                except Exception:
                    pass
        except Exception:
            pass

    def _shortcut_toggle_log_both(self):
        grid = self.graph_grid
        if grid:
            plot_widgets = []
            for lw in grid.lookup_windows:
                if hasattr(lw, 'plot_widget'):
                    plot_widgets.append(lw.plot_widget)
            cursor_pos = QCursor.pos()
            for pw in plot_widgets:
                if pw.geometry().contains(pw.mapFromGlobal(cursor_pos)):
                    try:
                        pi = pw.getPlotItem()
                        if pi is not None:
                            cur_x = pi.getAxis('bottom').logMode
                            cur_y = pi.getAxis('left').logMode
                            if cur_x and cur_y:
                                # Both on log, turn both off
                                new_x = False
                                new_y = False
                            elif not cur_x and not cur_y:
                                # Both off log, turn both on
                                new_x = True
                                new_y = True
                            else:
                                # One on, one off, turn both on to make consistent
                                new_x = True
                                new_y = True
                            pi.setLogMode(x=new_x, y=new_y)
                            pi_id = id(pi)
                            self._plot_log_state[pi_id] = {'x': new_x, 'y': new_y}

                        # Sync checkboxes
                        plw = getattr(pw, 'parent_lookup_window', None)
                        if plw and hasattr(plw, 'sync_log_checkboxes'):
                            plw.sync_log_checkboxes()
                    except Exception:
                        pass
                    break

    def _shortcut_toggle_log_x(self):
        grid = self.graph_grid
        if grid:
            plot_widgets = []
            for lw in grid.lookup_windows:
                if hasattr(lw, 'plot_widget'):
                    plot_widgets.append(lw.plot_widget)
            cursor_pos = QCursor.pos()
            for pw in plot_widgets:
                if pw.geometry().contains(pw.mapFromGlobal(cursor_pos)):
                    try:
                        pi = pw.getPlotItem()
                        if pi is not None:
                            cur_x = pi.getAxis('bottom').logMode
                            cur_y = pi.getAxis('left').logMode
                            new_x = not cur_x
                            pi.setLogMode(x=new_x, y=cur_y)
                            pi_id = id(pi)
                            self._plot_log_state[pi_id] = {'x': new_x, 'y': cur_y}

                        # Sync checkboxes
                        plw = getattr(pw, 'parent_lookup_window', None)
                        if plw and hasattr(plw, 'sync_log_checkboxes'):
                            plw.sync_log_checkboxes()
                    except Exception:
                        pass
                    break

    def _shortcut_toggle_log_y(self):
        grid = self.graph_grid
        if grid:
            plot_widgets = []
            for lw in grid.lookup_windows:
                if hasattr(lw, 'plot_widget'):
                    plot_widgets.append(lw.plot_widget)
            cursor_pos = QCursor.pos()
            for pw in plot_widgets:
                if pw.geometry().contains(pw.mapFromGlobal(cursor_pos)):
                    try:
                        pi = pw.getPlotItem()
                        if pi is not None:
                            cur_x = pi.getAxis('bottom').logMode
                            cur_y = pi.getAxis('left').logMode
                            new_y = not cur_y
                            pi.setLogMode(x=cur_x, y=new_y)
                            pi_id = id(pi)
                            self._plot_log_state[pi_id] = {'x': cur_x, 'y': new_y}

                        # Sync checkboxes
                        plw = getattr(pw, 'parent_lookup_window', None)
                        if plw and hasattr(plw, 'sync_log_checkboxes'):
                            plw.sync_log_checkboxes()
                    except Exception:
                        pass
                    break

    def _shortcut_auto_fit(self):
        grid = self.graph_grid
        if grid:
            cursor_pos = QCursor.pos()
            for lw in grid.lookup_windows:
                # ── 3D mode: reset GL camera ──
                gl_w = getattr(lw, 'gl_widget', None)
                if gl_w is not None and gl_w.isVisible():
                    if gl_w.geometry().contains(gl_w.mapFromGlobal(cursor_pos)):
                        try:
                            lw.auto_fit_3d()
                        except Exception:
                            pass
                        return
                # ── 2D mode: auto-range the plot view ──
                pw = getattr(lw, 'plot_widget', None)
                if pw is not None:
                    if pw.geometry().contains(pw.mapFromGlobal(cursor_pos)):
                        try:
                            vb = pw.getViewBox()
                            if vb is not None:
                                vb.enableAutoRange()
                        except Exception:
                            pass
                        return

    def _shortcut_add_vertical_marker(self):
        def h(pw):
            try:
                pw.add_vertical_marker()
            except Exception:
                pass
        self._apply_to_plotwidgets(h)

    def _shortcut_add_horizontal_marker(self):
        def h(pw):
            try:
                pw.add_horizontal_marker()
            except Exception:
                pass
        self._apply_to_plotwidgets(h)

    def _find_active_3d_widget(self):
        """Return the ROAR3DViewWidget under the cursor if visible, else None."""
        grid = getattr(self, 'graph_grid', None)
        if not grid:
            return None
        cursor_pos = QCursor.pos()
        for lw in getattr(grid, 'lookup_windows', []):
            gl_w = getattr(lw, 'gl_widget', None)
            if gl_w is not None and gl_w.isVisible():
                if gl_w.geometry().contains(gl_w.mapFromGlobal(cursor_pos)):
                    return gl_w
        return None



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ROARApp()
    window_icon = QIcon(ROAR_HOME + "/images/png/ROAR_ICON_256x256.png")
    window.setWindowIcon(window_icon)
    window.show()
    sys.exit(app.exec())
