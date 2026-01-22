import sys
import os
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
    QMessageBox, QMenuBar, QMenu, QFileDialog, QStatusBar, QRadioButton, QTabBar)
from PyQt6.QtCore import Qt, QSize, QObject, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QAction, QColor, QPen, QKeySequence
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

# from PySide6.QtCore import Qt
import pyqtgraph as pg
import pyqtgraph.opengl as gl
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

DEBUG = False
DEBUG_DESIGN = True

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
        layout.addWidget(self.tree)

        self.tree_item_counter = 0
        self.tech_dict = tech_dict if tech_dict is not None else top_level_app.tech_dict

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
            self.lookup_window.update_graph_from_tech_browser()

    def handle_item_changed(self, item, column):
        check_state = item.checkState(0)
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, check_state)
        if self.startup == True:
            # self.startup = False
            return 0
        self.lookup_window.update_graph_from_tech_browser()

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
        self.logo_image_path = ROAR_HOME + "/images/png/ROAR_LOGO_W100_H282_px.png"
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

        # Add widgets to layout
        layout.addWidget(self.graph_calc_icon)
        layout.addWidget(self.layout_button)
        layout.addStretch()  # Pushes everything else to the left
        layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)


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

        # Window properties
        self.setWindowTitle("ROAR - Robust Optimal Analog Reuse")
        self.setGeometry(100, 100, 1200, 800)

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
            design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "single_transistor_basic_variables.json")
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
                widget.add_tech_luts(dirname=dir, pdk_name=pdk_name)
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

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # ----- SOLVER MENU -----
        solver_menu = menubar.addMenu("Solver")

        run_solver_action = QAction("Run Solver", self)
        run_solver_action.triggered.connect(self.run_solver)

        stop_solver_action = QAction("Stop Solver", self)
        stop_solver_action.triggered.connect(self.stop_solver)

        solver_prefs_action = QAction("Preferences", self)
        solver_prefs_action.triggered.connect(self.open_solver_preferences)

        solver_menu.addAction(run_solver_action)
        solver_menu.addAction(stop_solver_action)
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

        # ----- EXPORT MENU -----
        export_menu = menubar.addMenu("Export")
        export_action = QAction("Export Data", self)
        export_action.triggered.connect(self.export_data)
        export_menu.addAction(export_action)

        # ----- HELP MENU -----
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    # ---- MENU ACTION CALLBACKS ----
    def new_file(self):
        """Handler for New File action."""
        QMessageBox.information(self, "New File", "New file creation is not implemented yet.")

    def open_file(self):
        """Opens a file dialog to open a file."""
        filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*.*)")
        if filename:
            QMessageBox.information(self, "Open File", f"File opened: {filename}")

    def save_file(self):
        """Opens a file dialog to save a file."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", "", "All Files (*.*)")
        if filename:
            QMessageBox.information(self, "Save File", f"File saved: {filename}")

    def run_solver(self):
        """Placeholder function for running solver."""
        QMessageBox.information(self, "Run Solver", "Solver started.")

    def stop_solver(self):
        """Placeholder function for stopping solver."""
        QMessageBox.warning(self, "Stop Solver", "Solver stopped.")

    def open_solver_preferences(self):
        """Opens solver preferences."""
        QMessageBox.information(self, "Preferences", "Solver preferences dialog is not implemented yet.")

    def open_window_preferences(self):
        """Opens window preferences."""
        QMessageBox.information(self, "Preferences", "Window preferences dialog is not implemented yet.")

    def export_data(self):
        """Handles data export."""
        QMessageBox.information(self, "Export", "Data export feature is not implemented yet.")

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
            # fallback to raw key constant
            key = event.key()
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
        def h(pw):
            try:
                try:
                    with open('/tmp/roar_shortcuts.log', 'a', encoding='utf-8') as fh:
                        fh.write(f"TOGGLE_BOTH target={type(pw)} id={getattr(pw,'_pi_id',None)}\n")
                except Exception:
                    pass

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
        self._apply_to_plotwidgets(h)

    def _shortcut_toggle_log_x(self):
        def h(pw):
            try:
                try:
                    with open('/tmp/roar_shortcuts.log', 'a', encoding='utf-8') as fh:
                        fh.write(f"TOGGLE_X target={type(pw)} id={getattr(pw,'_pi_id',None)}\n")
                except Exception:
                    pass

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
        self._apply_to_plotwidgets(h)

    def _shortcut_toggle_log_y(self):
        def h(pw):
            try:
                try:
                    with open('/tmp/roar_shortcuts.log', 'a', encoding='utf-8') as fh:
                        fh.write(f"TOGGLE_Y target={type(pw)} id={getattr(pw,'_pi_id',None)}\n")
                except Exception:
                    pass

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
        self._apply_to_plotwidgets(h)

    def _shortcut_auto_fit(self):
        def h(pw):
            try:
                try:
                    with open('/tmp/roar_shortcuts.log', 'a', encoding='utf-8') as fh:
                        fh.write(f"AUTO_FIT target={type(pw)} id={getattr(pw,'_pi_id',None)}\n")
                except Exception:
                    pass

                vb = pw.getViewBox()
                if vb is not None:
                    vb.enableAutoRange()
            except Exception:
                pass
        self._apply_to_plotwidgets(h)

# Custom QTabBar that forwards right-clicks to the application's tab context menu
class ROARTabBar(QTabBar):
    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def mousePressEvent(self, event):
        # If right-click, forward to owner context menu with tab-local position
        try:
            if event.button() == Qt.MouseButton.RightButton and self.owner is not None:
                # Call the owner's context menu handler with the tab-bar-local position
                self.owner._on_tab_context_menu(event.pos())
                # consume event
                return
        except Exception:
            pass
        super().mousePressEvent(event)


# Global event filter to capture key presses application-wide (L/X/Y/F)
class _GlobalKeyFilter(QObject):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.KeyPress:
                # log what we see for debugging (text() may be empty depending on IME/focus)
                try:
                    txt = event.text() or ''
                except Exception:
                    txt = ''
                key = event.key()
                try:
                    with open('/tmp/roar_keys.log', 'a', encoding='utf-8') as fh:
                        fh.write(f"GlobalKeyFilter: text={repr(txt)} key={key} mods={int(event.modifiers())}\n")
                except Exception:
                    pass

                ch = txt.lower() if txt else None
                # Prefer textual match (lowercase) but fall back to key constants
                if ch == 'l' or key == Qt.Key.Key_L:
                    try:
                        self.owner._shortcut_toggle_log_both()
                        event.accept()
                        return True
                    except Exception:
                        pass
                if ch == 'x' or key == Qt.Key.Key_X:
                    try:
                        self.owner._shortcut_toggle_log_x()
                        event.accept()
                        return True
                    except Exception:
                        pass
                if ch == 'y' or key == Qt.Key.Key_Y:
                    try:
                        self.owner._shortcut_toggle_log_y()
                        event.accept()
                        return True
                    except Exception:
                        pass
                if ch == 'f' or key == Qt.Key.Key_F:
                    try:
                        self.owner._shortcut_auto_fit()
                        event.accept()
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False


if __name__ == '__main__':
    # Run the application when executed as a script. Use a defensive wrapper
    # so any exceptions print to stderr instead of causing a silent exit.
    try:
        try:
            with open('/tmp/roar_debug.log', 'a', encoding='utf-8') as _fh:
                _fh.write('entrypoint start\n')
        except Exception:
            pass
         # Ensure Qt uses the same binding selected earlier
        try:
            from PyQt6.QtWidgets import QApplication
        except Exception:
            # fallback: try importing from separate module
            from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)

        main_win = ROARApp()
        main_win.show()
        # start event loop
        exit_code = app.exec()
        sys.exit(exit_code)
    except Exception as e:
        # Print full traceback to stderr to aid debugging
        import traceback, sys as _sys
        traceback.print_exc()
        _sys.exit(1)

