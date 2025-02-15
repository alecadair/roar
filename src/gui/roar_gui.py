import sys
import os
import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QSplitter, QHBoxLayout, 
    QLineEdit, QLabel, QTextEdit, QCheckBox, QColorDialog, QTreeWidget, QTreeWidgetItem, 
    QScrollBar, QFileDialog, QInputDialog, QComboBox, QSpinBox, QGridLayout, QSizePolicy,
    QMessageBox, QMenuBar, QMenu, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QAction, QColor
from PySide6.QtCore import Qt
import pyqtgraph as pg
import qdarktheme

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cid import CIDDevice
from design_editor import *
from generator import *

# Environment variables
ROAR_HOME = os.environ.get("ROAR_HOME", "")
ROAR_LIB = os.environ.get("ROAR_LIB", "")
ROAR_SRC = os.environ.get("ROAR_SRC", "")
ROAR_CHARACTERIZATION = os.environ.get("ROAR_CHARACTERIZATION", "")
ROAR_DESIGN_SCRIPTS = os.environ.get("ROAR_DESIGN", "")

DEBUG = True

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
        #self.tree.itemClicked.connect(self.select_item)
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
        #graph_grid.add_tech_luts(dirname=dir, pdk_name=pdk_name)
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

    def set_graphing_widget(self, graphing_widget):
        self.graphing_widget = graphing_widget

    def add_tech_luts(self, dirname=None, pdk_name=None):
        print("Adding technology from directory" + dirname)
        print("PDK Name: " + pdk_name)
        if dirname is None:
            dirname = QFileDialog.getExistingDirectory(self, "Select Directory")
            if not dirname:
                return  # User canceled

            pdk_name, ok = QInputDialog.getText(self, "Technology Process Name", "Enter name of process i.e. sky130, process_soi_22")
            if not ok or not pdk_name.strip():
                return  # User canceled or empty input

        #pdk_item = QTreeWidgetItem([pdk_name])
        #self.tree.addTopLevelItem(pdk_item)
        pdk_dict = None
        if self.top_level_app is not None:
            pdk_dict = self.top_level_app.tech_dict
            #pdk_dict = self.top_level_app.tech_dict.get(pdk_name, {})
        else:
            pdk_dict = ROARTechBrowser.create_tech_dict_from_dir(dirname, pdk_name)

        delim = ">"
        pdk_item = QTreeWidgetItem([pdk_name])
        pdk_item.setFlags(pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        pdk_item.setCheckState(0, Qt.CheckState.Unchecked)
        self.pdk_item.addChild(pdk_item)
        for pdk, pdk_subdict in pdk_dict.items():
            pdk_subitem = QTreeWidgetItem([pdk])
            pdk_subitem.setFlags(pdk_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            pdk_subitem.setCheckState(0, Qt.CheckState.Unchecked)
            pdk_subitem.addChild(pdk_item)
            for model, model_dict in pdk_subdict.items():
                model_item = QTreeWidgetItem([model])
                model_item.setFlags(model_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                model_item.setCheckState(0, Qt.CheckState.Unchecked)
                pdk_item.addChild(model_item)
                for length, length_dict in model_dict.items():
                    length_item = QTreeWidgetItem([length])
                    length_item.setFlags(length_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    length_item.setCheckState(0, Qt.CheckState.Unchecked)
                    model_item.addChild(length_item)
                    for corner, corners_dict in length_dict["corners"].items():
                        corner_item = QTreeWidgetItem([corner])
                        corner_item.setFlags(corner_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        corner_item.setCheckState(0, Qt.CheckState.Unchecked)
                        length_item.addChild(corner_item)



class ROARLookupWindow(QWidget):
    def __init__(self, parent, expand_callback, top_level_app, graph_grid=None):
        super().__init__(parent)
        self.expand_callback = expand_callback
        self.top_level_app = top_level_app
        self.graph_grid = graph_grid  # Store reference to ROARGraphGrid
        self.is_expanded = False  # Track expansion state
        self.original_state = None  # Store splitter state

        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Create the horizontal splitter for tech browser + controls (left) and graphing window (right)
        self.top_level_pane = QSplitter(Qt.Orientation.Horizontal, self)

        # Create the vertical splitter to split tech browser (top) from controls (bottom)
        self.tech_splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Initialize the tech browser widget
        self.tech_browser = ROARTechBrowser(self, lookup_window=self, top_level_app=self.top_level_app, tech_dict=tech_dict)

        if DEBUG == False:
            self.tech_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create a container for control widgets
        self.controls_container = QWidget()
        self.controls_layout = QGridLayout(self.controls_container)

        # Individual Labels, ComboBoxes, and SpinBoxes for X, Y, and Z
        self.label_x = QLabel("X:")
        self.combo_x = QComboBox()
        self.combo_x.addItems(["kgm", "kco", "kgd", "iden"])
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(0.0, 100.0)
        self.checkbox_logx = QCheckBox("LogX")

        self.label_y = QLabel("Y:")
        self.combo_y = QComboBox()
        self.combo_y.addItems(["kgm", "kco", "kgd", "iden"])
        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(0.0, 100.0)
        self.checkbox_logy = QCheckBox("LogY")

        self.label_z = QLabel("Z:")
        self.combo_z = QComboBox()
        self.combo_z.addItems(["kgm", "kco", "kgd", "iden"])
        self.spin_z = QDoubleSpinBox()
        self.spin_z.setRange(0.0, 100.0)
        self.checkbox_logz = QCheckBox("LogZ")

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

        # Update button spanning the first row
        self.update_button = QPushButton("Update")
        self.controls_layout.addWidget(self.update_button, 0, 0, 1, 4)

        # Individual Checkboxes with specific callbacks
        self.checkbox_3d = QCheckBox("3-D")
        self.checkbox_contour = QCheckBox("Contour")
        self.checkbox_legend = QCheckBox("Legend")
        self.checkbox_black_bg = QCheckBox("Black BG")

        self.controls_layout.addWidget(self.checkbox_3d, 4, 1)
        self.controls_layout.addWidget(self.checkbox_contour, 4, 2)
        self.controls_layout.addWidget(self.checkbox_legend, 4, 3)
        #self.controls_layout.addWidget(self.checkbox_black_bg, 4, 3)

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

        # Initialize the graphing window
        #self.graphing_window = ROARPlotWidget(self, top_level_app=self.top_level_app)
        self.plot_widget = pg.PlotWidget()
        #self.plot_scientific_data()
        #self.plot_widget = pg.GraphicsLayoutWidget()  # Wrap it in a QWidget-compatible class
        #self.plot = self.plot_widget.addPlot()
        #self.plot_container = QWidget()
        #self.layout = QVBoxLayout(self.plot_container)
        #layout.addWidget(self.plot_widget)
        #self.plot_container.setLayout(layout)
        # Uncomment the following when not debugging
        if DEBUG == False:
            self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Add widgets to the main horizontal splitter
        self.top_level_pane.addWidget(self.tech_splitter)  # Left side (tech browser + controls)
        self.test_widget = QWidget()
        self.plot_widget = self.test_widget
        #self.top_level_pane.addWidget(self.plot_widget)  # Right side (graphing window)
        self.top_level_pane.addWidget(self.plot_widget)  # Right side (graphing window)

        # Adjust stretch factors for main splitter (tech section gets less space than graphing)
        self.top_level_pane.setStretchFactor(0, 1)
        self.top_level_pane.setStretchFactor(1, 2)

        # Add splitter to the main layout
        self.main_layout.addWidget(self.top_level_pane)
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.is_dark_mode = False
        self.is_3d_mode = False
        self.colors = [pg.mkPen(color) for color in ['r', 'g', 'b', 'y']]
        self.current_color_index = 0

        # Auto-plot different colored sine waves on startup
        #self.plot_scientific_data()
        self.expand_button.clicked.connect(self.toggle_expand)

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

    def update_graph_from_tech_browser(self, equation_eval=None):
        models_selected = self.tech_browser.tree.get_checked()
        self.graphing_window.ax.cla()
        self.graphing_window.canvas.draw()
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                      'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                      'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        color_index = 0

        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[0]
            model_name = model_tokens[1]
            length = model_tokens[2]
            corner = model_tokens[3]
            cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            if equation_eval != None:
                print("TODO")
                return 0
            #cid_corner = self.graph_controller.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            param1 = self.graphing_window.x_dropdown.get()
            param2 = self.graphing_window.y_dropdown.get()
            legend_str = pdk + " " + model_name + " " + length + " " + corner
            color = color_list[color_index]
            #cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
            #                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str, show_legend=self.legend_var.get())
            self.graphing_window.ax.grid(True, which="both")

            color_index += 1
            if color_index >= len(color_list):
                color_index = 0
            #self.graphing_window.canvas.draw()
            self.graphing_window.canvas.draw()

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
        #self.toggle_browser_button = QPushButton(">")
        #self.toggle_browser_button.setFixedWidth(30)
        #self.toggle_browser_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        #self.toggle_browser_button.clicked.connect(self.toggle_browser)
        #self.banner_layout.addWidget(self.toggle_browser_button)

        # X selection
        self.x_label = QLabel("X:")
        self.banner_layout.addWidget(self.x_label)

        self.x_dropdown = QComboBox()
        self.x_dropdown.addItems(self.top_level_app.lookups)
        if DEBUG == False:
            self.x_dropdown.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.banner_layout.addWidget(self.x_dropdown)

        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(0, 100)
        self.x_spinbox.setSingleStep(0.1)
        self.x_spinbox.setValue(15)
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

        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(0, 100)
        self.y_spinbox.setSingleStep(0.1)
        self.y_spinbox.setValue(15)
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

        # Update Button
        self.update_button = QPushButton("Update")
        self.update_button.setFixedWidth(80)
        if DEBUG == False:
            self.update_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.update_button.clicked.connect(self.update_graph)
        self.banner_layout.addWidget(self.update_button)

        # Set up layouts
        self.main_layout.addLayout(self.banner_layout)
        self.setLayout(self.main_layout)

    def toggle_browser(self):
        """Placeholder function for toggling the browser"""
        print("Toggle browser button clicked")

    def update_graph(self):
        """Calls the update graph function provided"""
        self.update_graph_callback()

class ROARPlotWidget(QWidget):
    def __init__(self, parent=None, top_level_app=None):
        super().__init__(parent)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        #bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout = QGridLayout()
        self.plot_widget = pg.PlotWidget()
        self.lookup_banner = ROARPlotLookupBanner(top_level_app, self.plot_scientific_data, self)
        self.dark_mode_checkbox = QCheckBox("Enable Dark Mode")
        self.dark_mode_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        bottom_buttons_layout.addWidget(self.dark_mode_checkbox, 0, 0)

        self.three_d_checkbox = QCheckBox("Enable 3D Rendering")
        self.three_d_checkbox.stateChanged.connect(self.toggle_three_d_mode)
        bottom_buttons_layout.addWidget(self.three_d_checkbox, 1, 0)

        self.color_button = QPushButton("Change Plot Colors")
        self.color_button.clicked.connect(self.change_plot_colors)
        bottom_buttons_layout.addWidget(self.color_button, 0, 1)

        self.expand_button = QPushButton("Expand Plot")
        self.expand_button.clicked.connect(self.expand_plot)
        bottom_buttons_layout.addWidget(self.expand_button, 1, 1)

        plot_layout.addWidget(self.lookup_banner)
        plot_layout.addWidget(self.plot_widget)
        plot_layout.addLayout(bottom_buttons_layout)



        splitter.addWidget(plot_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self.is_dark_mode = False
        self.is_3d_mode = False
        self.colors = [pg.mkPen(color) for color in ['r', 'g', 'b', 'y']]
        self.current_color_index = 0
        
        # Auto-plot different colored sine waves on startup
        self.plot_scientific_data()

    def expand_plot(self):
        print("TODO")

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


    def plot_scientific_data(self):
        self.plot_widget.clear()
        x = np.linspace(0, 10, 100)
        for i, color in enumerate(self.colors):
            y = np.sin(x + i)
            self.plot_widget.plot(x, y, pen=color)


class ROARHeader(QWidget):
    def __init__(self, parent=None, top_level_app=None):
        super().__init__(parent)

        # Set a taller fixed height for the header
        self.roar_teal = '#1C8091'
        banner_height = 72
        self.setFixedHeight(banner_height)  # Increased height for better spacing
        #self.setAutoFillBackground(True)  # Ensures the background color applies

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
        logo_scale = banner_height/64
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(logo_pixmap)
            self.logo_label.setScaledContents(True)  # Ensures it resizes correctly
            self.logo_label.setFixedSize(int(181*logo_scale), int(64*logo_scale))  # Adjust logo size to match header
        else:
            self.logo_label.setText("Logo not found")  # Debugging fallback

        # Create buttons with icons
        self.graph_calc_icon = QPushButton()
        icon_pixmap = QPixmap(self.graph_calc_icon_path)
        if not icon_pixmap.isNull():
            icon = QIcon(icon_pixmap)
            self.graph_calc_icon.setIcon(icon)
            self.graph_calc_icon.setIconSize(icon_pixmap.rect().size())  # Ensure full-size icon
        button_scale = banner_height/64
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
        self.grid_splitter.setChildrenCollapsible(False)
        if DEBUG == False:
            self.grid_splitter.setSizePolicy(self.grid_splitter.sizePolicy())
        self.grid_splitter.setChildrenCollapsible(False)
        
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)
        if DEBUG == False:
            self.top_splitter.setSizePolicy(self.top_splitter.sizePolicy())
        self.top_splitter.setChildrenCollapsible(False)
        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(False)
        if DEBUG == False:
            self.bottom_splitter.setSizePolicy(self.bottom_splitter.sizePolicy())
        self. bottom_splitter.setChildrenCollapsible(False)


        self.lookup_window_1 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_window_2 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_window_3 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_window_4 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)

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


class ROARApp(QMainWindow):
    def __init__(self, tech_dict=None):
        super().__init__()
        self.roar_design = ROARDesign()
        # Define lookup variables
        self.lookups = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'csb', 'css', 'ft', 'gds', 'gm', 'gmb',
                        'gmidft', 'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgds', 'kgm',
                        'kgmft', 'n', 'rds', 'ro', 'va', 'vds', 'vdsat', 'vgs', 'vth')
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

        # Add ROARHeader at the top
        self.header = ROARHeader(self, top_level_app=self)
        main_layout.addWidget(self.header)

        # Create a horizontal splitter
        splitter_h = QSplitter(Qt.Orientation.Horizontal)
        self.editor_window = ROAREditorWindow(top_level_app=self)
        splitter_h.addWidget(self.editor_window)

        self.graph_grid = ROARGraphGrid(parent=self, top_level_app=self)
        splitter_h.addWidget(self.graph_grid)

        # Add splitter to the layout
        main_layout.addWidget(splitter_h)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Initialize menu bar
        self.init_menu_bar()

        sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
        predictive_28 = "/home/adair/Documents/CAD/roar/characterization/predictive_28/LUTs_1V8_mac"
        self.add_tech_luts(dir=predictive_28, pdk_name="jp28")
        #self.add_tech_luts(dir=predictive_28, pdk_name="predictive28_1v8")

    def add_tech_luts(self, dir, pdk_name):
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir, filename)
            if os.path.isdir(f):
                model_name = filename
                self.create_devices_from_model_dir(pdk_name=pdk_name, model_name=model_name, model_dir=f)
        self.graph_grid.add_tech_luts(dirname=dir, pdk_name=pdk_name)
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
        return(self.tech_dict)


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
        QMessageBox.about(self, "About ROAR", "ROAR - Robust Optimal Analog Reuse\nVersion 1.0\n© 2024 ROAR Inc.")


if __name__ == "__main__":
    #qdarktheme.enable_hi_dpi()
    #app = QApplication([sys.argv])
    app = QApplication([])
    #qdarktheme.setup_theme("light")
    #qdarktheme.setup_theme("auto")
    #qdarktheme.setup_theme()
    #test = "test_tech_browser"
    #test = "test_plot_widget"
    #test = "test_lookup_window"
    #test = "test_window_grid"
    test = ""
    window = QMainWindow()
    sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
    tech_dict = ROARTechBrowser.create_tech_dict_from_dir(sky130_luts, "Skywater130A")

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
        window = ROARApp(tech_dict)
        #window.setCentralWidget(app_widget)
    #window.setStyle("Fusion")
    window.show()
    sys.exit(app.exec())
