import sys
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"
import numpy as np
#import pyqtgraph.opengl as gl

from PyQt6.QtWidgets import (
    QDoubleSpinBox, QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QSplitter, QHBoxLayout,
    QLineEdit, QLabel, QTextEdit, QCheckBox, QColorDialog, QTreeWidget, QTreeWidgetItem,
    QScrollBar, QFileDialog, QInputDialog, QComboBox, QSpinBox, QGridLayout, QSizePolicy,
    QMessageBox, QMenuBar, QMenu, QFileDialog, QStatusBar, QRadioButton, QTabBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QAction, QColor, QPen
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"

# from PySide6.QtCore import Qt
import pyqtgraph as pg
import qdarktheme

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cid import CIDDevice
from design_editor import *
from generator import *
from equation_solver import *

# Environment variables
ROAR_HOME = os.environ.get("ROAR_HOME", "")
ROAR_LIB = os.environ.get("ROAR_LIB", "")
ROAR_SRC = os.environ.get("ROAR_SRC", "")
ROAR_CHARACTERIZATION = os.environ.get("ROAR_CHARACTERIZATION", "")
ROAR_DESIGN_SCRIPTS = os.environ.get("ROAR_DESIGN", "")

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


class ROARLookupWindow(QWidget):
    def __init__(self, parent, expand_callback, top_level_app, graph_grid=None):
        super().__init__(parent)
        self.expand_callback = expand_callback
        self.top_level_app = top_level_app
        self.graph_grid = graph_grid  # Store reference to ROARGraphGrid
        self.is_expanded = False  # Track expansion state
        self.original_state = None  # Store splitter state
        self.expression_symbols = []
        self._is_updating = False

        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        left, top, right, bottom = self.main_layout.getContentsMargins()

        # Set a new left margin value, keeping the others unchanged
        new_left_margin = 3
        self.main_layout.setContentsMargins(new_left_margin, top, right, bottom)
        #self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # Create the horizontal splitter for tech browser + controls (left) and graphing window (right)
        self.top_level_pane = QSplitter(Qt.Orientation.Horizontal, self)

        # Create the vertical splitter to split tech browser (top) from controls (bottom)
        self.tech_splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Initialize the tech browser widget. Use the top-level app's tech_dict
        # when available to avoid referencing a possibly undefined global `tech_dict`.
        try:
            td = self.top_level_app.tech_dict if (self.top_level_app and hasattr(self.top_level_app, 'tech_dict')) else None
        except Exception:
            td = None
        self.tech_browser = ROARTechBrowser(self, lookup_window=self, top_level_app=self.top_level_app, tech_dict=td)

        # if DEBUG == False:
        self.tech_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tech_browser.startup = False

        # Create a container for control widgets
        self.controls_container = QWidget()
        self.controls_layout = QGridLayout(self.controls_container)

        # Radio buttons for parameter source
        self.radio_device_params = QRadioButton("Device Params")
        self.radio_design_eq = QRadioButton("Design Eqs")
        self.radio_device_params.setChecked(True)
        # Track current mode on the instance (True = Device Params, False = Design Eqs)
        self.is_device_params_mode = self.radio_device_params.isChecked()
        self.checkbox_legend = QCheckBox("Legend")

        # store the radio layout on the instance so other methods can reference it
        self.radio_layout = QHBoxLayout()
        self.radio_layout.addWidget(self.radio_device_params)
        self.radio_layout.addWidget(self.radio_design_eq)
        self.radio_layout.addStretch()
        self.controls_layout.addLayout(self.radio_layout, 0, 0, 1, 3)
        self.controls_layout.addWidget(self.checkbox_legend, 0, 3)

        # Connect toggled signal(s) to keep mode variable in sync and update UI
        self.radio_device_params.toggled.connect(self.on_mode_changed)
        self.radio_design_eq.toggled.connect(self.on_mode_changed)

        # Individual Labels, ComboBoxes, and SpinBoxes for X, Y, and Z
        self.label_x = QLabel("X:")
        self.combo_x = QComboBox()
        self.combo_x.addItems(self.top_level_app.lookups)
        self.combo_x.setCurrentText("kgm")
        # Keep combo boxes left-aligned and do not allow them to expand horizontally
        self.combo_x.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_x = EngSpinBox()
        self.spin_x.setMinimumWidth(120)
        # Make spinboxes expand horizontally to absorb extra space
        self.spin_x.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logx = QCheckBox("LogX")

        self.label_y = QLabel("Y:")
        self.combo_y = QComboBox()
        self.combo_y.addItems(self.top_level_app.lookups)
        self.combo_y.setCurrentText("kcgs")
        self.combo_y.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_y = EngSpinBox()
        self.spin_y.setMinimumWidth(120)
        self.spin_y.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logy = QCheckBox("LogY")

        self.label_z = QLabel("Z:")
        self.combo_z = QComboBox()
        self.combo_z.addItems(self.top_level_app.lookups)
        self.combo_z.setCurrentText("iden")
        self.combo_z.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_z = EngSpinBox()
        self.spin_z.setMinimumWidth(120)
        self.spin_z.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logz = QCheckBox("LogZ")

        # Clear markers / update graph when changing axes
        self.combo_x.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_y.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_z.currentIndexChanged.connect(self.on_axis_selection_changed)

        self.controls_layout.addWidget(self.label_x, 1, 0)
        self.controls_layout.addWidget(self.combo_x, 1, 1)
        self.controls_layout.addWidget(self.spin_x, 1, 2)
        self.controls_layout.addWidget(self.checkbox_logx, 1, 3)

        self.controls_layout.addWidget(self.label_y, 2, 0)
        self.controls_layout.addWidget(self.combo_y, 2, 1)
        self.controls_layout.addWidget(self.spin_y, 2, 2)
        self.controls_layout.addWidget(self.checkbox_logy, 2, 3)

        self.controls_layout.addWidget(self.label_z, 3, 0)
        self.controls_layout.addWidget(self.combo_z, 3, 1)
        self.controls_layout.addWidget(self.spin_z, 3, 2)
        self.controls_layout.addWidget(self.checkbox_logz, 3, 3)

        # Set column stretch factors
        # Make the spinner column stretch (absorb extra space) while other columns remain tight
        self.controls_layout.setColumnStretch(0, 0)
        self.controls_layout.setColumnStretch(1, 0)
        self.controls_layout.setColumnStretch(2, 1) # Spinner column expands
        self.controls_layout.setColumnStretch(3, 0)

        # Individual Checkboxes with specific callbacks
        self.checkbox_3d = QCheckBox("3-D")
        self.checkbox_contour = QCheckBox("Contour")
        self.checkbox_black_bg = QCheckBox("Black BG")

        # We'll place the 3-D/Contour checkboxes and Copy/Settings buttons dynamically
        # inside update_combobox_items() so their positions change depending on
        # whether Device Params or Design Eqs is selected.
        self.copy_button = QPushButton("Copy")
        self.settings_button = QPushButton("Settings")
        self.controls_layout.addWidget(self.copy_button, 5, 0, 1, 2)
        self.controls_layout.addWidget(self.settings_button, 5, 2, 1, 2)
        # Expand button spanning the bottom row
        self.expand_button = QPushButton("Expand")
        self.controls_layout.addWidget(self.expand_button, 6, 0, 1, 4)

        # Add widgets to the vertical splitter
        self.tech_splitter.addWidget(self.tech_browser)  # Tech browser (top)
        self.tech_splitter.addWidget(self.controls_container)  # Controls (bottom)

        # Adjust stretch factors for tech splitter (tech browser gets more space than controls)
        self.tech_splitter.setStretchFactor(0, 3)
        self.tech_splitter.setStretchFactor(1, 1)
        # self.plot_widget = pg.PlotWidget()
        self.plot_widget = ROARPlotWidget(parent_lookup_window=self, top_level_app=self.top_level_app)
        # Uncomment the following when not debugging
        # if DEBUG == False:

        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Add widgets to the main horizontal splitter
        self.top_level_pane.addWidget(self.tech_splitter)  # Left side (tech browser + controls)
        # self.test_widget = QWidget()
        # self.plot_widget = self.test_widget
        # self.top_level_pane.addWidget(self.plot_widget)  # Right side (graphing window)
        self.top_level_pane.addWidget(self.plot_widget)  # Right side (graphing window)

        # Adjust stretch factors for main splitter (tech section gets less space than graphing)
        self.top_level_pane.setStretchFactor(0, 1)
        self.top_level_pane.setStretchFactor(1, 2)

        # Add splitter to the main layout
        self.main_layout.addWidget(self.top_level_pane)
        # self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.is_dark_mode = False
        self.is_3d_mode = False
        self.colors = [pg.mkPen(color) for color in ['r', 'g', 'b', 'y']]
        self.color_list = [Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue,
                           Qt.GlobalColor.cyan, Qt.GlobalColor.magenta, Qt.GlobalColor.yellow]
        self.style_list = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine]
        self.current_color_index = 0
        self.current_style_index = 0

        # Auto-plot different colored sine waves on startup
        # self.plot_scientific_data()
        self.expand_button.clicked.connect(self.toggle_expand)

        self.checkbox_logx.stateChanged.connect(self.update_log_scale)
        self.checkbox_logy.stateChanged.connect(self.update_log_scale)

        self.checkbox_3d.stateChanged.connect(self._update_z_controls_state)
        self._update_z_controls_state()

        # Ensure combo boxes and visibility reflect the current radio selection
        self.update_combobox_items()

    def update_combobox_items(self):
        is_device_params = self.radio_device_params.isChecked()

        # Update visibility of Z-axis and 3D controls
        self.label_z.setVisible(not is_device_params)
        self.combo_z.setVisible(not is_device_params)
        self.spin_z.setVisible(not is_device_params)
        self.checkbox_logz.setVisible(not is_device_params)
        self.checkbox_3d.setVisible(not is_device_params)
        self.checkbox_contour.setVisible(not is_device_params)

        # Do not attempt to reparent widgets here; only update visibility and contents.
        # Keep the legend checkbox in its layout position and control visibility if needed.
        self.checkbox_legend.setVisible(True)

        if is_device_params:
            items = list(self.top_level_app.lookups) if self.top_level_app else []
            # populate with device lookup names and set device defaults
            self.combo_x.clear()
            self.combo_y.clear()
            self.combo_z.clear()
            self.combo_x.addItems(items)
            self.combo_y.addItems(items)
            self.combo_z.addItems(items)
            self.combo_x.setCurrentText("kgm")
            self.combo_y.setCurrentText("kcgs")
            self.combo_z.setCurrentText("iden")
        else:
            items = list(self.expression_symbols) if self.expression_symbols else []
            self.combo_x.clear()
            self.combo_y.clear()
            self.combo_z.clear()
            self.combo_x.addItems(items)
            self.combo_y.addItems(items)
            self.combo_z.addItems(items)

            if items:
                self.combo_x.setCurrentIndex(0)
                self.combo_y.setCurrentIndex(min(1, len(items) - 1))
                self.combo_z.setCurrentIndex(min(2, len(items) - 1))

        # Reposition the 3-D / Contour checkboxes and Copy/Settings buttons so that
        # when Design Eqs is selected the checkboxes are to the left of the buttons
        # on the same row, and when Device Params is selected the checkboxes are hidden
        # and the buttons shift left without leaving blank space.
        try:
            # Remove widgets from any previous positions (safe to call repeatedly)
            self.controls_layout.removeWidget(self.copy_button)
            self.controls_layout.removeWidget(self.settings_button)
            self.controls_layout.removeWidget(self.checkbox_3d)
            self.controls_layout.removeWidget(self.checkbox_contour)
        except Exception:
            pass

        if is_device_params:
            # Hide the 3-D/Contour checkboxes and place Copy/Settings left-aligned
            self.checkbox_3d.hide()
            self.checkbox_contour.hide()
            self.controls_layout.addWidget(self.copy_button, 5, 0, 1, 2)
            self.controls_layout.addWidget(self.settings_button, 5, 2, 1, 2)
        else:
            # Show checkboxes and place them to the left of the Copy/Settings buttons
            self.checkbox_3d.show()
            self.checkbox_contour.show()
            self.controls_layout.addWidget(self.checkbox_3d, 5, 0)
            self.controls_layout.addWidget(self.checkbox_contour, 5, 1)
            self.controls_layout.addWidget(self.copy_button, 5, 2)
            self.controls_layout.addWidget(self.settings_button, 5, 3)

        if not is_device_params:
            self._update_z_controls_state()

    def on_mode_changed(self, _checked):
        """Keep the boolean mode in sync with the radio buttons and refresh UI."""
        # Update the stored mode flag
        self.is_device_params_mode = self.radio_device_params.isChecked()
        # Refresh the UI to match the new mode
        self.update_combobox_items()

    def update_expression_symbols(self, symbols):
        self.expression_symbols = symbols
        self.update_combobox_items()

    def _update_z_controls_state(self):
        is_3d = self.checkbox_3d.isChecked()
        self.label_z.setEnabled(is_3d)
        self.combo_z.setEnabled(is_3d)
        self.spin_z.setEnabled(is_3d)
        self.checkbox_logz.setEnabled(is_3d)
        self.checkbox_contour.setEnabled(is_3d)

    def clear_markers(self):
        """Remove all markers and their text from the plot and clear the markers list."""
        pw = getattr(self, "plot_widget", None)
        if not pw:
            return
        # Remove items safely
        for marker_info in pw.markers[:]:
            try:
                if "marker" in marker_info and marker_info["marker"] is not None:
                    pw.plotItem.removeItem(marker_info["marker"])
                if "text" in marker_info and marker_info["text"] is not None:
                    pw.plotItem.removeItem(marker_info["text"])
            except Exception:
                pass
        pw.markers.clear()

    def sync_log_checkboxes(self):
        x_log = self.plot_widget.getPlotItem().getAxis('bottom').logMode
        y_log = self.plot_widget.getPlotItem().getAxis('left').logMode

        self.checkbox_logx.setChecked(x_log)
        self.checkbox_logy.setChecked(y_log)

    def update_log_scale(self):
        self.plot_widget.getPlotItem().setLogMode(x=self.checkbox_logx.isChecked(), y=self.checkbox_logy.isChecked())
        self.update_graph_from_tech_browser()

    def on_axis_selection_changed(self, _idx=None):
        """Called when X/Y/Z selection changes: clear markers, update graph, then autofit (same as 'F' hotkey)."""
        try:
            self.clear_markers()
        except Exception:
            pass
        try:
            self.update_graph_from_tech_browser()
        except Exception:
            pass
        # Auto-fit view (same as F hotkey)
        try:
            if hasattr(self, 'plot_widget') and self.plot_widget is not None:
                self.plot_widget.plotItem.autoRange()
        except Exception:
            pass

    def toggle_expand(self):
        """
        Expand this widget to take the full grid space or restore it back.
        """
        if not self.is_expanded:
            self.expand_plot()
        else:
            self.contract_plot()

    def expand_plot(self):
        """ Expands the current lookup window to take up the full splitter space. """
        if not self.graph_grid:
            return  # Ensure we have a valid graph grid reference

        grid = self.graph_grid  # Use stored reference

        # Save the original state of the splitters
        self.original_state = grid.grid_splitter.saveState()

        # Remove all widgets except this one
        grid.lookup_window_1.setParent(None)
        grid.lookup_window_2.setParent(None)
        grid.lookup_window_3.setParent(None)
        grid.lookup_window_4.setParent(None)

        # Add only this widget to the splitter
        grid.grid_splitter.addWidget(self)
        grid.grid_splitter.setStretchFactor(0, 1)

        # Update state
        self.is_expanded = True
        self.expand_button.setText("Contract")

    def contract_plot(self):
        """ Restores the original grid layout with all lookup windows. """
        if not self.graph_grid or not self.original_state:
            return  # Ensure we have a saved state

        grid = self.graph_grid

        # Restore the splitter state
        grid.grid_splitter.restoreState(self.original_state)

        # Re-add all widgets
        grid.grid_splitter.addWidget(grid.top_splitter)
        grid.grid_splitter.addWidget(grid.bottom_splitter)

        # Restore top and bottom splitters
        grid.top_splitter.addWidget(grid.lookup_window_1)
        grid.top_splitter.addWidget(grid.lookup_window_2)
        grid.bottom_splitter.addWidget(grid.lookup_window_3)
        grid.bottom_splitter.addWidget(grid.lookup_window_4)

        # Update state
        self.is_expanded = False
        self.expand_button.setText("Expand")

    def toggle_dark_mode(self):
        self.is_dark_mode = self.dark_mode_checkbox.isChecked()
        self.plot_widget.setBackground('k' if self.is_dark_mode else 'w')
        self.plot_scientific_data()

    def toggle_three_d_mode(self):
        self.is_3d_mode = self.three_d_checkbox.isChecked()
        self.plot_scientific_data()

    def change_plot_colors(self):
        for i in range(len(self.colors)):
            color = QColorDialog.getColor()
            if color.isValid():
                self.colors[i] = pg.mkPen(color.name())
        self.plot_scientific_data()

    def plot_scientific_data(self):
        self.plot_widget.clear()
        x = np.linspace(0, 10, 100)
        for i, color in enumerate(self.colors):
            y = np.sin(x + i)
            self.plot_widget.plot(x, y, pen=color)

    def select_item(self, item, column):
        if self.lookup_window is not None:
            self.lookup_window.update_graph_from_tech_browser()

    def get_corner_dfs_from_models_selected(self):
        models_selected = self.tech_browser.get_checked_item_paths()
        corner_dfs = []
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[1]
            model_name = model_tokens[2]
            length = model_tokens[3]
            corner = model_tokens[4]
            cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            corner_df = cid_corner.df
            corner_dfs.append(corner_df)
        return corner_dfs

    def update_graph_from_tech_browser(self, equation_eval=None):
        if self._is_updating:
            return
        self._is_updating = True

        try:
            models_selected = self.tech_browser.get_checked_item_paths()

            # Store marker positions before clearing
            marker_positions = []
            for marker_info in self.plot_widget.markers:
                marker_positions.append(marker_info)

            # Check if the plot is empty before clearing, to enable auto-fitting for the first trace
            auto_fit = not self.plot_widget.plotItem.curves

            self.plot_widget.clear()
            self.plot_widget.markers.clear()

            if not models_selected:
                self.plot_widget.getPlotItem().setXRange(0, 1)
                self.plot_widget.getPlotItem().setYRange(0, 1)
                self.plot_widget.getPlotItem().setTitle("")
                self.plot_widget.getPlotItem().setLabel('left', "")
                self.plot_widget.getPlotItem().setLabel('bottom', "")
                self._is_updating = False
                return

            self.current_color_index = 0
            self.current_style_index = 0
            new_plot = True

            for model in models_selected:
                model_tokens = model.split(">")
                pdk = model_tokens[1]
                model_name = model_tokens[2]
                length = model_tokens[3]
                corner = model_tokens[4]
                cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
                if equation_eval != None:
                    print("TODO")
                    continue

                param1 = self.combo_x.currentText()
                param2 = self.combo_y.currentText()

                if self.current_color_index >= len(self.color_list):
                    self.current_color_index = 0
                    self.current_style_index += 1
                    if self.current_style_index >= len(self.style_list):
                        self.current_style_index = 0

                color = self.color_list[self.current_color_index]
                style = self.style_list[self.current_style_index]
                graph_pen = pg.mkPen(color=QColor(color), style=style, width=1)

                if self.is_device_params_mode:
                    unit1 = ""
                    unit2 = ""
                    if param1 in self.top_level_app.lookups_units_dict:
                        unit1 = self.top_level_app.lookups_units_dict[param1]
                    if param2 in self.top_level_app.lookups_units_dict:
                        unit2 = self.top_level_app.lookups_units_dict[param2]

                    cid_corner.plot_processes_params_roar_plot_widget(param1=param1, param2=param2, param3=None, norm_type="",
                                                                      show_plot=True, new_plot=new_plot,
                                                                      roar_plot_widget=self.plot_widget,
                                                                      color=color, legend_str=None, enable_3d=False,
                                                                      pen=graph_pen, unit1=unit1, unit2=unit2)
                else:
                    unit1 = ""
                    unit2 = ""
                    equation_solver = ROAREquationSolver(top_level_app=self.top_level_app)
                    # Give the solver access to the current corner data frames for lookup substitution
                    equation_solver.corners = [cid_corner.df]
                    expressions, constraints = self.top_level_app.editor_window.get_expressions_and_constraints()
                    for expression_sym in expressions:
                        expression = expressions[expression_sym]
                        equation_solver.add_equation(expression_sym, expression)
                    result_matrix = equation_solver.evaluate_equations(symbols_to_add=[param1, param2], corner_dfs=[cid_corner.df])
                    # Defensive checks: ensure result_matrix exists and contains the requested params
                    if not result_matrix or not isinstance(result_matrix, dict):
                        msg = f"Design Eq solver returned no results for {param1},{param2}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue
                    if param1 not in result_matrix or param2 not in result_matrix:
                        msg = f"Design Eq results missing requested symbols: {param1} or {param2}. Available: {list(result_matrix.keys())}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue
                    params1 = result_matrix[param1]
                    params2 = result_matrix[param2]
                    # Coerce to 1-D numpy arrays for plotting
                    try:
                        arr1 = np.asarray(params1)
                        arr2 = np.asarray(params2)
                        # If scalar, expand to vector with length of dataframe rows
                        if arr1.ndim == 0:
                            nrows = cid_corner.df.shape[0] if hasattr(cid_corner, 'df') else (arr1.size if hasattr(arr1, 'size') else 1)
                            arr1 = np.full(nrows, float(arr1))
                        if arr2.ndim == 0:
                            nrows = cid_corner.df.shape[0] if hasattr(cid_corner, 'df') else (arr2.size if hasattr(arr2, 'size') else 1)
                            arr2 = np.full(nrows, float(arr2))
                        # If shape is (N,1) or (N,1,1) collapse to (N,)
                        if arr1.ndim > 1:
                            arr1 = arr1.reshape(arr1.shape[0], -1)
                            if arr1.shape[1] == 1:
                                arr1 = arr1[:, 0]
                            else:
                                arr1 = arr1.ravel()
                        if arr2.ndim > 1:
                            arr2 = arr2.reshape(arr2.shape[0], -1)
                            if arr2.shape[1] == 1:
                                arr2 = arr2[:, 0]
                            else:
                                arr2 = arr2.ravel()
                        params1 = arr1.ravel()
                        params2 = arr2.ravel()
                    except Exception:
                        try:
                            params1 = np.asarray(params1).squeeze()
                            params2 = np.asarray(params2).squeeze()
                        except Exception:
                            pass
                    # After coercion, ensure both are 1-D numpy arrays of same length
                    try:
                        params1 = np.asarray(params1)
                        params2 = np.asarray(params2)
                        if params1.size == 0 or params2.size == 0:
                            msg = f"Design Eq plotting: empty data for {param1}/{param2}"
                            print(msg)
                            try:
                                if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                    self.top_level_app.statusBar().showMessage(msg, 5000)
                            except Exception:
                                pass
                            continue
                        # If lengths differ, trim to the smaller length
                        if params1.shape[0] != params2.shape[0]:
                            nmin = min(params1.shape[0], params2.shape[0])
                            params1 = params1[:nmin]
                            params2 = params2[:nmin]
                    except Exception:
                        pass
                    # Now plot the design-equation results
                    try:
                        curve = self.plot_widget.plot(params1, params2, pen=graph_pen, name=None)
                        # Set labels
                        xlabel = param1 + "  [" + unit1 + "]"
                        ylabel = param2 + "  [" + unit2 + "]"
                        self.plot_widget.setLabel('bottom', xlabel)
                        self.plot_widget.setLabel('left', ylabel)
                        self.plot_widget.setTitle(f"{param2} vs {param1}")
                        self.plot_widget.getAxis('left').setStyle(autoExpandTextSpace=True)
                        self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
                    except Exception as e:
                        msg = f"Plotting error for design eq {param1} vs {param2}: {e}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                new_plot = False
                self.plot_widget.showGrid(x=True, y=True)
                self.current_color_index += 1

            if auto_fit:
                self.plot_widget.plotItem.autoRange()

            # Re-plot markers
            for marker_info in marker_positions:
                x, y = marker_info['pos']

                x_log = self.plot_widget.getPlotItem().getAxis('bottom').logMode
                y_log = self.plot_widget.getPlotItem().getAxis('left').logMode

                plot_x = np.log10(x) if x_log and x > 0 else x
                plot_y = np.log10(y) if y_log and y > 0 else y

                marker = pg.ScatterPlotItem(x=[plot_x], y=[plot_y], symbol='o', size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
                self.plot_widget.plotItem.addItem(marker)

                text = pg.TextItem(f"({format_eng(x)}, {format_eng(y)})", anchor=(0.5, 1.5))
                text.setPos(plot_x, plot_y)
                self.plot_widget.plotItem.addItem(text)

                self.plot_widget.markers.append({"marker": marker, "text": text, "pos": (x, y)})
        finally:
            self._is_updating = False
        return 0

    def add_tech_luts(self, dirname, pdk_name):
        self.tech_browser.add_tech_luts(dirname=dirname, pdk_name=pdk_name)


class ROARPlotSettings(QWidget):
    def __init__(self, parent=None, top_level_app=None):
        super().__init__(parent)


class ROARPlotLookupBanner(QWidget):
    def __init__(self, top_level_app, update_graph_callback, parent=None):
        super().__init__(parent)

        self.top_level_app = top_level_app
        self.update_graph_callback = update_graph_callback

        # Layouts
        self.main_layout = QVBoxLayout(self)
        self.banner_layout = QHBoxLayout()

        # Toggle browser button
        # self.toggle_browser_button = QPushButton(">")
        # self.toggle_browser_button.setFixedWidth(30)
        # self.toggle_browser_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # self.toggle_browser_button.clicked.connect(self.toggle_browser)
        # self.banner_layout.addWidget(self.toggle_browser_button)

        # X selection
        self.x_label = QLabel("X:")
        self.banner_layout.addWidget(self.x_label)

        self.x_dropdown = QComboBox()
        self.x_dropdown.addItems(self.top_level_app.lookups)
        if DEBUG == False:
            self.x_dropdown.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.x_dropdown)

        self.x_spinbox = EngSpinBox()
        self.x_spinbox.setRange(0, 100)
        self.x_spinbox.setSingleStep(0.1)
        self.x_spinbox.setValue(15)
        self.x_spinbox.setMinimumWidth(120)
        if DEBUG == False:
            self.x_spinbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.x_spinbox)

        # Y selection
        self.y_label = QLabel("Y:")
        self.banner_layout.addWidget(self.y_label)

        self.y_dropdown = QComboBox()
        self.y_dropdown.addItems(self.top_level_app.lookups)
        if DEBUG == False:
            self.y_dropdown.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.y_dropdown)

        self.y_spinbox = EngSpinBox()
        self.y_spinbox.setRange(0, 100)
        self.y_spinbox.setSingleStep(0.1)
        self.y_spinbox.setValue(15)
        self.y_spinbox.setMinimumWidth(120)
        if DEBUG == False:
            self.y_spinbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.y_spinbox)

        # Lookup Label
        self.lookup_label = QLabel()
        if DEBUG == False:
            self.lookup_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.lookup_label)

        # Add a spacer to push the update button to the right
        self.banner_layout.addStretch()

        # Update Button removed
        # self.update_button = QPushButton("Update")
        # self.update_button.setFixedWidth(80)
        # # if DEBUG == False:
        # self.update_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # self.update_button.clicked.connect(self.update_graph)
        # self.banner_layout.addWidget(self.update_button)

        # Set up layouts
        self.main_layout.addLayout(self.banner_layout)
        self.setLayout(self.main_layout)

    def toggle_browser(self):
        """Placeholder function for toggling the browser"""
        print("Toggle browser button clicked")

    def update_graph(self):
        """Calls the update graph function provided"""
        self.update_graph_callback()



class ROARPlotWidget(pg.PlotWidget):
    def __init__(self, *args, top_level_app=None, parent_lookup_window=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.top_level_app = top_level_app
        self.parent_lookup_window = parent_lookup_window
        self._mouse_inside = False

        # Add legend and crosshair lines
        self.plotItem.addLegend()
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DotLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DotLine))
        self.plotItem.addItem(self.v_line, ignoreBounds=True)
        self.plotItem.addItem(self.h_line, ignoreBounds=True)
        # Add text item for coordinates
        self.coord_text = pg.TextItem(anchor=(0, 1))
        self.plotItem.addItem(self.coord_text)
        self.coord_text.setZValue(100)

        # Initialize markers list
        self.markers = []

        # Connect mouse events
        self.scene().sigMouseMoved.connect(self.on_mouse_moved)
        self.scene().sigMouseClicked.connect(self.on_mouse_clicked)
        self.plotItem.vb.sigStateChanged.connect(self.on_state_changed)

    def on_state_changed(self, _):
        if self.parent_lookup_window:
            self.parent_lookup_window.sync_log_checkboxes()

    def enterEvent(self, event):
        self._mouse_inside = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_inside = False
        if self.top_level_app and hasattr(self.top_level_app, "coord_label"):
            self.top_level_app.coord_label.setText("Coordinates: ")
        super().leaveEvent(event)

    def on_mouse_moved(self, pos):
        if self._mouse_inside and self.plotItem.sceneBoundingRect().contains(pos):
            # Only update coordinates if there are items in the plot
            if not self.plotItem.curves:
                return

            mouse_point = self.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            x_log = self.plotItem.getAxis('bottom').logMode
            y_log = self.plotItem.getAxis('left').logMode

            display_x = 10**x if x_log else x
            display_y = 10**y if y_log else y

            if self.top_level_app and hasattr(self.top_level_app, "coord_label"):
                self.top_level_app.coord_label.setText(f"Coordinates: ({format_eng(display_x)}, {format_eng(display_y)})")

            self.coord_text.setText(f"x={format_eng(display_x)}, y={format_eng(display_y)}")
            self.coord_text.setPos(mouse_point)
            self.v_line.setPos(x)
            self.h_line.setPos(y)

    def on_mouse_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()
            if self.plotItem.sceneBoundingRect().contains(scene_pos):
                mouse_point = self.plotItem.vb.mapSceneToView(scene_pos)

                for marker_info in self.markers:
                    marker_item = marker_info["marker"]
                    if self.is_close(marker_item.getData()[0][0], marker_item.getData()[1][0], mouse_point.x(), mouse_point.y()):
                        self.plotItem.removeItem(marker_info["marker"])
                        self.plotItem.removeItem(marker_info["text"])
                        self.markers.remove(marker_info)
                        return

                closest_curve, closest_point_index = self.find_closest_point(mouse_point)

                if closest_curve is not None and closest_point_index is not None:
                    x_data, y_data = closest_curve.getData()
                    x, y = x_data[closest_point_index], y_data[closest_point_index]

                    x_log = self.plotItem.getAxis('bottom').logMode
                    y_log = self.plotItem.getAxis('left').logMode

                    # Store the true linear value of the marker
                    store_x = 10**x if x_log else x
                    store_y = 10**y if y_log else y

                    marker = pg.ScatterPlotItem(x=[x], y=[y], symbol='o', size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
                    self.plotItem.addItem(marker)

                    text = pg.TextItem(f"({format_eng(store_x)}, {format_eng(store_y)})", anchor=(0.5, 1.5))
                    text.setPos(x, y)
                    self.plotItem.addItem(text)

                    self.markers.append({"marker": marker, "text": text, "pos": (store_x, store_y)})

                    # Update parent lookup window spinboxes (expand ranges if needed)
                    plw = getattr(self, "parent_lookup_window", None)
                    if plw:
                        try:
                            spinx = getattr(plw, "spin_x", None)
                            spiny = getattr(plw, "spin_y", None)
                            if isinstance(spinx, QDoubleSpinBox):
                                self._ensure_spinbox_range(spinx, store_x)
                                spinx.setValue(store_x)
                            if isinstance(spiny, QDoubleSpinBox):
                                self._ensure_spinbox_range(spiny, store_y)
                                spiny.setValue(store_y)
                        except Exception:
                            # Don't raise on UI update errors
                            pass

    def _ensure_spinbox_range(self, spinbox: QDoubleSpinBox, value: float, margin: float = 0.1):
        """
        Expand the given QDoubleSpinBox range so `value` can be set without being clamped.
        """
        try:
            cur_min = spinbox.minimum()
            cur_max = spinbox.maximum()
            # If the incoming value is outside current range, expand by a small margin
            if value < cur_min:
                new_min = value - max(abs(value) * margin, 1e-12)
                spinbox.setMinimum(new_min)
            if value > cur_max:
                new_max = value + max(abs(value) * margin, 1e-12)
                spinbox.setMaximum(new_max)
        except Exception:
            # Be defensive: don't let a spinbox error break marker placement
            pass

    def find_closest_point(self, mouse_point):
        closest_curve = None
        closest_point_index = None
        min_dist_sq = float('inf')

        mouse_pos_scene = self.plotItem.vb.mapViewToScene(mouse_point)

        for curve in self.getPlotItem().curves:
            x_data, y_data = curve.getData()
            if x_data is None or y_data is None:
                continue

            for i in range(len(x_data)):
                point_view = pg.Point(x_data[i], y_data[i])
                point_scene = self.plotItem.vb.mapViewToScene(point_view)

                dist_sq = (point_scene.x() - mouse_pos_scene.x())**2 + (point_scene.y() - mouse_pos_scene.y())**2

                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_curve = curve
                    closest_point_index = i

        # Check if the closest point is reasonably close to the mouse click (in pixels)
        if min_dist_sq > 75**2: # 75 pixels tolerance
            return None, None

        return closest_curve, closest_point_index

    def is_close(self, x1, y1, x2, y2):
        p1 = self.plotItem.vb.mapViewToScene(pg.Point(x1, y1))
        p2 = self.plotItem.vb.mapViewToScene(pg.Point(x2, y2))
        return (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2 < 10**2 # 10 pixels tolerance

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F and self._mouse_inside:
            self.plotItem.autoRange()
        elif event.key() == Qt.Key.Key_X and self._mouse_inside:
            if self.parent_lookup_window:
                self.parent_lookup_window.checkbox_logx.toggle()
        elif event.key() == Qt.Key.Key_Y and self._mouse_inside:
            if self.parent_lookup_window:
                self.parent_lookup_window.checkbox_logy.toggle()
        elif event.key() == Qt.Key.Key_L and self._mouse_inside:
            if self.parent_lookup_window:
                log_x_checked = self.parent_lookup_window.checkbox_logx.isChecked()
                log_y_checked = self.parent_lookup_window.checkbox_logy.isChecked()
                new_state = not (log_x_checked and log_y_checked)
                self.parent_lookup_window.checkbox_logx.setChecked(new_state)
                self.parent_lookup_window.checkbox_logy.setChecked(new_state)
        else:
            super().keyPressEvent(event)


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


class ROARGraphGrid(QWidget):
    def __init__(self, parent=None, top_level_app=None, tech_dict=None):
        super().__init__(parent)
        self.lookup_windows = []
        layout = QVBoxLayout(self)
        self.top_level_app = top_level_app

        self.grid_splitter = QSplitter(Qt.Orientation.Vertical)
        self.grid_splitter.setChildrenCollapsible(True)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(True)

        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(True)

        # Top left lookup window in grid
        self.lookup_window_1 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app,
                                                graph_grid=self)
        # Top right lookup window in grid
        self.lookup_window_2 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app,
                                                graph_grid=self)
        # Bottom left lookup window in grid
        self.lookup_window_3 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app,
                                                graph_grid=self)
        # Bottom right lookup window in grid
        self.lookup_window_4 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app,
                                                graph_grid=self)

        self.lookup_windows.append(self.lookup_window_1)
        self.lookup_windows.append(self.lookup_window_2)
        self.lookup_windows.append(self.lookup_window_3)
        self.lookup_windows.append(self.lookup_window_4)

        self.top_splitter.addWidget(self.lookup_window_1)
        self.top_splitter.addWidget(self.lookup_window_2)

        self.bottom_splitter.addWidget(self.lookup_window_3)
        self.bottom_splitter.addWidget(self.lookup_window_4)

        self.grid_splitter.addWidget(self.top_splitter)
        self.grid_splitter.setStretchFactor(0, 1)
        self.grid_splitter.addWidget(self.bottom_splitter)
        self.grid_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.grid_splitter)

    def add_tech_luts(self, dirname, pdk_name):
        for lookup_window in self.lookup_windows:
            lookup_window.add_tech_luts(dirname=dirname, pdk_name=pdk_name)

    def populate_from_app(self):
        """Populate this grid's lookup windows from the top-level app's tech_dict.

        This is used when a new tab is created, to initialize its lookup windows
        with the same technology LUTs and expression symbols as existing tabs.
        """
        try:
            # Ensure we have the latest tech_dict and expressions from the top-level app
            app_tech = getattr(self.top_level_app, 'tech_dict', None)
            # Get expression symbols from editor window if available
            expr_symbols = []
            try:
                expressions, constraints = self.top_level_app.editor_window.get_expressions_and_constraints()
                expr_symbols = list(expressions.keys()) if expressions else []
            except Exception:
                expr_symbols = []

            for lookup_window in self.lookup_windows:
                try:
                    tb = getattr(lookup_window, 'tech_browser', None)
                    if tb is not None:
                        tb.tech_dict = app_tech if app_tech is not None else {}
                        tb.populate_from_tech_dict()
                        tb.startup = False

                    # Update the lookup window's expression symbols and refresh comboboxes
                    lookup_window.update_expression_symbols(expr_symbols)
                    lookup_window.update_combobox_items()
                except Exception:
                    # Continue initializing other lookup windows even if one fails
                    pass
        except Exception:
            pass


class ROARApp(QMainWindow):
    def __init__(self, tech_dict=None):
        super().__init__()
        self.roar_design = ROARDesign()
        roar_images = ROAR_HOME + "/images/png/"
        self.setWindowIcon(QIcon(roar_images + "ROAR_ICON.png"))
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
        self.graph_tabs.tabCloseRequested.connect(lambda idx: self.close_graph_tab(idx))
        # Enable right-click context menu on the tab bar for Rename/Close/Set Color
        try:
            self.graph_tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.graph_tabs.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)
        except Exception:
            pass
        # Use the custom tab bar that forwards right-clicks to ROARApp._on_tab_context_menu
        try:
            custom_bar = ROARTabBar(owner=self)
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

        sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
        predictive_28 = ROAR_CHARACTERIZATION + "/predictive_28/LUTs_1V8_mac"
        ihp130_luts = ROAR_CHARACTERIZATION + "/ihp130/LUTs_IHP130"
        #self.add_tech_luts(dir=predictive_28, pdk_name="jp28")
        self.add_tech_luts(dir=sky130_luts, pdk_name="SKY130A")
        #self.add_tech_luts(dir=ihp130_luts, pdk_name="IHP-SG13G2")

        # self.add_tech_luts(dir=predictive_28, pdk_name="predictive28_1v8")i
        #self.equation_solver = ROAREquationSolver(top_level_app=self,data_frames=[])

        if DEBUG_DESIGN:
            #design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "cs2.json")
            design_path = os.path.join(ROAR_DESIGN_SCRIPTS, "single_transistor_basic_variables.json")
            self.editor_window.load_all_data(file_path=design_path, show_success_message=False)

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

            return grid
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create graph tab: {e}")
            return None

    def close_graph_tab(self, index: int):
        """Close the tab at `index`. Always ensure at least one tab remains."""
        try:
            if index < 0 or index >= self.graph_tabs.count():
                return
            # Do not allow closing the '+' add-tab
            if self.graph_tabs.tabText(index) == '+':
                return
            widget = self.graph_tabs.widget(index)
            self.graph_tabs.removeTab(index)
            try:
                widget.deleteLater()
            except Exception:
                pass
            # If no tabs left, create a new one
            # Ensure there's at least one real tab (not counting '+')
            real_tabs = [i for i in range(self.graph_tabs.count()) if self.graph_tabs.tabText(i) != '+']
            if not real_tabs:
                self.create_new_graph_tab()
            # Update active reference
            cur = self.graph_tabs.currentWidget()
            self.graph_grid = cur
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

# Custom QTabBar that forwards right-clicks to the application's tab context menu
class ROARTabBar(QTabBar):
    def __init__(self, owner=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def mousePressEvent(self, event):
        # If right-click, forward to owner context menu handler with tab-local position
        try:
            if event.button() == Qt.MouseButton.RightButton and self.owner is not None:
                # Call the owner's context menu handler with the tab-bar-local position
                self.owner._on_tab_context_menu(event.pos())
                # consume event
                return
        except Exception:
            pass
        super().mousePressEvent(event)

if __name__ == "__main__":
    # Wrap execution in a try/except to surface any exceptions when running
    # from environments (like PyCharm) that might otherwise swallow them.
    try:
        print("\nInitializing ROAR GUI Application...\n")
        # If running on Linux without a DISPLAY or Wayland session, Qt may exit
        # silently. Detect that and print a helpful message rather than failing
        # with no output.
        if sys.platform.startswith('linux'):
            has_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
            if not has_display:
                print("ERROR: No X11/Wayland display found (DISPLAY or WAYLAND_DISPLAY not set).")
                print("If you're running headless, start with Xvfb: e.g.")
                print("  xvfb-run -s \"-screen 0 1280x800x24\" python3 src/gui/roar_gui.py")
                print("Or run this from a desktop session where DISPLAY is set.")
                sys.exit(1)

        app = QApplication(sys.argv)
        # qdarktheme.setup_theme("light")
        # qdarktheme.setup_theme("auto")
        # qdarktheme.setup_theme()

        tech_dict = None
        window = None
        test = ""

        if test in ["test_tech_browser", "test_plot_widget", "test_lookup_window", "test_window_grid"]:
            window = QMainWindow()

        if test == "test_tech_browser":
            test_widget = ROARTechBrowser(window, None, None, tech_dict={})
            test_widget.add_tech_luts(dirname=sky130_luts, pdk_name="Skywater130A")
            window.setCentralWidget(test_widget)
        elif test == "test_plot_widget":
            test_widget = ROARPlotWidget(window)
            window.setCentralWidget(test_widget)
        elif test == "test_lookup_window":
            test_widget = ROARLookupWindow(window, None, None, tech_dict=tech_dict)
            window.setCentralWidget(test_widget)
        elif test == "test_window_grid":
            test_widget = ROARGraphGrid(window, None, tech_dict=tech_dict)
            window.setCentralWidget(test_widget)
        else:
            window = ROARApp()

        print("Showing main window...")
        window.show()
        print("Starting Qt event loop...")
        ret = app.exec()
        print(f"Qt event loop exited with return code: {ret}")
        sys.exit(ret)
    except Exception:
        import traceback, sys as _sys
        traceback.print_exc()
        # Ensure non-zero exit on exception
        _sys.exit(1)
