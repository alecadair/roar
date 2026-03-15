from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QMessageBox, QSplitter, QGroupBox,
    QDialog, QRadioButton, QCheckBox, QLabel, QProgressDialog, QMenu
)
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QColor, QBrush, QPalette, QPainter, QPen, QIcon, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import json
import sys
import os


# Get ROAR_HOME from environment
ROAR_HOME = os.environ.get("ROAR_HOME", "")


class DeviceCornerSelectorWindow(QDialog):
    """Window with tech browser for selecting corners for a specific device instance."""

    corners_selected = pyqtSignal(object)  # Emits None for global or list of corner names

    def __init__(self, parent, device_name, tech_browser_ref, current_corners=None):
        super().__init__(parent)
        self.device_name = device_name
        self.tech_browser_ref = tech_browser_ref
        self.current_corners = current_corners
        self.selected_corners = current_corners  # Track current selection

        self.setWindowTitle(f"Select Corners for {device_name}")
        self.setMinimumSize(600, 500)

        # Make it non-modal so user can interact with main window
        self.setModal(False)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info label (stored as instance attribute so switch_device can update it)
        self.info_label = QLabel(f"Select corners for device: <b>{self.device_name}</b>")
        self.info_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(self.info_label)

        # Create or reference the tech browser
        self.tech_browser = None

        if self.tech_browser_ref:
            # Import the tech browser class
            try:
                from .roar_gui import ROARTechBrowser
            except Exception:
                try:
                    from roar_gui import ROARTechBrowser
                except Exception:
                    ROARTechBrowser = None

            if ROARTechBrowser:
                try:
                    # Create a new tech browser instance that SHARES the same data
                    # Get necessary references from the parent tech browser
                    lookup_window = None
                    top_level_app = None
                    tech_dict = None

                    if hasattr(self.tech_browser_ref, 'lookup_window'):
                        lookup_window = self.tech_browser_ref.lookup_window
                    if hasattr(self.tech_browser_ref, 'top_level_app'):
                        top_level_app = self.tech_browser_ref.top_level_app
                    if hasattr(self.tech_browser_ref, 'tech_dict'):
                        tech_dict = self.tech_browser_ref.tech_dict

                    # ROARTechBrowser accepts tech_dict parameter and shares the same data
                    self.tech_browser = ROARTechBrowser(
                        parent=self,
                        lookup_window=lookup_window,
                        top_level_app=top_level_app,
                        tech_dict=tech_dict  # Share the same data structure!
                    )

                    # Populate the tree with data from tech_dict
                    if hasattr(self.tech_browser, 'populate_from_tech_dict'):
                        self.tech_browser.populate_from_tech_dict()

                    # If we have current custom corners, check them in the tech browser
                    if self.current_corners:
                        self.apply_corner_selection_to_browser(self.current_corners)

                    layout.addWidget(self.tech_browser)
                except Exception as e:
                    print(f"Could not create tech browser: {e}")
                    import traceback
                    traceback.print_exc()
                    error_label = QLabel(f"Error creating tech browser: {e}")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)

        if not self.tech_browser:
            no_browser_label = QLabel("Tech browser not available")
            no_browser_label.setStyleSheet("color: gray; font-style: italic; padding: 20px;")
            layout.addWidget(no_browser_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.apply_button = QPushButton("Apply")
        self.apply_button.setToolTip("Apply current corner selection to this device")
        self.apply_button.clicked.connect(self.apply_selection)

        self.clear_button = QPushButton("Use Global")
        self.clear_button.setToolTip("Use global (main tech browser) selection instead")
        self.clear_button.clicked.connect(self.apply_global)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def apply_corner_selection_to_browser(self, corner_info):
        """Check specific corners in the tech browser.

        Args:
            corner_info: list of dicts with 'name' and 'path' keys, or list
                         of plain corner-name strings (legacy format).
        """
        if not self.tech_browser or not corner_info:
            return

        try:
            # Build a set of full paths AND a set of plain corner names so we
            # can match whichever way the data was stored.
            target_paths = set()
            target_names = set()
            for c in corner_info:
                if isinstance(c, dict):
                    if c.get('path'):
                        target_paths.add(c['path'])
                    if c.get('name'):
                        target_names.add(c['name'])
                elif isinstance(c, str):
                    target_names.add(c)

            # ── Strategy 1: use path_to_item for an exact match ──
            if hasattr(self.tech_browser, 'path_to_item') and target_paths:
                for full_path, tree_item in self.tech_browser.path_to_item.items():
                    if full_path in target_paths:
                        tree_item.setCheckState(0, Qt.CheckState.Checked)
                    else:
                        tree_item.setCheckState(0, Qt.CheckState.Unchecked)
                return  # done

            # ── Strategy 2: walk the whole tree and match by corner name ──
            if hasattr(self.tech_browser, 'tree') and target_names:
                tree = self.tech_browser.tree

                def _walk(item):
                    """Recurse through every item; check leaf items whose
                    text matches a target corner name."""
                    for i in range(item.childCount()):
                        child = item.child(i)
                        if child.childCount() == 0:
                            # Leaf = corner item
                            name = child.text(0)
                            if name in target_names:
                                child.setCheckState(0, Qt.CheckState.Checked)
                            else:
                                child.setCheckState(0, Qt.CheckState.Unchecked)
                        else:
                            _walk(child)

                root = tree.invisibleRootItem()
                _walk(root)

        except Exception as e:
            print(f"Error applying corner selection to browser: {e}")
            import traceback
            traceback.print_exc()

    def get_checked_corners_from_browser(self):
        """Extract checked corner information (full paths) from tech browser.

        Returns:
            list of dict: Each dict contains {'name': corner_name, 'path': full_path}
        """
        if not self.tech_browser:
            return []

        corner_info_list = []

        try:
            if hasattr(self.tech_browser, 'get_checked_item_paths'):
                # get_checked_item_paths returns paths like "PDK>sky130>nfet>180n>TT"
                # where TT is the corner name
                paths = self.tech_browser.get_checked_item_paths()
                for path in paths:
                    # Path format: "PDK>pdk_name>device_type>length>corner"
                    parts = path.split('>')
                    if len(parts) >= 5:  # Need all parts including corner
                        corner_name = parts[4]  # Corner is the 5th part (index 4)
                        corner_info_list.append({
                            'name': corner_name,
                            'path': path,  # Full path: PDK>pdk_name>device_type>length>corner
                            'pdk': parts[1],
                            'model': parts[2],
                            'length': parts[3]
                        })
                    elif len(parts) >= 1:  # Fallback - use last part without metadata
                        corner_info_list.append({
                            'name': parts[-1],
                            'path': path,
                            'pdk': None,
                            'model': None,
                            'length': None
                        })
        except Exception as e:
            print(f"Error getting checked corners: {e}")
            import traceback
            traceback.print_exc()

        return corner_info_list

    def switch_device(self, device_name, current_corners=None):
        """Switch this window to target a different device instance.

        Updates the title, info label, and tech-browser check-state to reflect
        the new device without creating a new window.
        """
        self.device_name = device_name
        self.current_corners = current_corners
        self.selected_corners = current_corners

        # Update UI text
        self.setWindowTitle(f"Select Corners for {device_name}")
        if hasattr(self, 'info_label') and self.info_label:
            self.info_label.setText(f"Select corners for device: <b>{device_name}</b>")

        # Update tech browser check-state
        if self.tech_browser:
            # First uncheck everything
            try:
                if hasattr(self.tech_browser, 'tree'):
                    tree = self.tech_browser.tree
                    root = tree.invisibleRootItem()

                    def _uncheck_all(parent_item):
                        for i in range(parent_item.childCount()):
                            child = parent_item.child(i)
                            if child.childCount() == 0:
                                child.setCheckState(0, Qt.CheckState.Unchecked)
                            else:
                                _uncheck_all(child)

                    _uncheck_all(root)
            except Exception:
                pass

            # Then apply the new corners if any
            if current_corners:
                self.apply_corner_selection_to_browser(current_corners)

    def apply_selection(self):
        """Apply the current corner selection."""
        # Get checked corners from tech browser (now returns list of dicts with path info)
        corner_info_list = self.get_checked_corners_from_browser()

        if not corner_info_list:
            QMessageBox.warning(self, "No Corners Selected",
                              "Please select at least one corner in the tech browser, or click 'Use Global'.")
            return

        # Emit signal with corner info (list of dicts with name, path, pdk, model, length)
        self.corners_selected.emit(corner_info_list)

        # Show feedback with just corner names
        corner_names = [c['name'] for c in corner_info_list]
        msg = f"Applied: {', '.join(corner_names)} for {self.device_name}"

        if self.parent():
            try:
                # Try to show message in status bar if available
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'statusBar'):
                        parent.statusBar().showMessage(msg, 3000)
                        break
                    parent = parent.parent() if hasattr(parent, 'parent') else None
            except Exception:
                pass

        print(msg)

    def apply_global(self):
        """Apply global selection (None = use main tech browser)."""
        self.selected_corners = None
        self.corners_selected.emit(None)

        msg = f"Applied: Use global corners for {self.device_name}"

        if self.parent():
            try:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'statusBar'):
                        parent.statusBar().showMessage(msg, 3000)
                        break
                    parent = parent.parent() if hasattr(parent, 'parent') else None
            except Exception:
                pass

        print(msg)


class BaseEditor(QWidget):
    def __init__(self, title, columns, plot_button_text="Add LUT", plot_command=None, add_command=None, tech_browser=None, enable_corners=False):
        super().__init__()
        self.columns = columns
        self.plot_button_text = plot_button_text
        self.plot_command = plot_command
        self.tech_browser = tech_browser  # Reference to tech browser for getting available corners
        self.enable_corners = enable_corners  # Whether to enable corner selection (Design Eqs mode only)

        # Find the Corners column index if it exists
        self.corners_column_index = columns.index("Corners") if "Corners" in columns else -1

        #self.disabled_rows = set()
        #self.enabled_plot_rows = set()

        layout = QVBoxLayout()
        self.setLayout(layout)

        # If a title is provided, use a QGroupBox so the title appears in the widget border.
        if title:
            group = QGroupBox(title)
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(6, 6, 6, 6)  # tighter inner margins
            group.setLayout(group_layout)
            container_layout = group_layout
            # add the group box to the outer layout
            layout.addWidget(group)
        else:
            container_layout = layout

        # Create the TreeWidget (use a small subclass to ensure click selects the item)
        class ReorderableTreeWidget(QTreeWidget):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.on_reorder_callback = None

            def mousePressEvent(self, event):
                # Ensure the item under the mouse becomes selected when clicking
                # (unless user is using Ctrl/Shift to multi-select). This helps
                # selection and keyboard-driven moves.
                try:
                    modifiers = event.modifiers()
                    if not (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                        it = self.itemAt(event.pos())
                        if it is not None and not it.isSelected():
                            self.clearSelection()
                            it.setSelected(True)
                            self.setCurrentItem(it)
                except Exception:
                    pass
                super().mousePressEvent(event)

            def paintEvent(self, event):
                # Let the base class draw the items
                try:
                    super().paintEvent(event)
                except Exception:
                    # If base paint fails for any reason, still try to continue
                    try:
                        QTreeWidget.paintEvent(self, event)
                    except Exception:
                        pass

                # Draw a subtle grey line under the bottom-most top-level row
                try:
                    count = self.topLevelItemCount()
                    if count > 0:
                        last_item = self.topLevelItem(count - 1)
                        if last_item is not None:
                            rect = self.visualItemRect(last_item)
                            if rect.isValid():
                                painter = QPainter(self.viewport())
                                pen = QPen(QColor('#c0c0c0'))
                                pen.setWidth(1)
                                painter.setPen(pen)
                                # draw across entire viewport width at the bottom of the last item's rect
                                y = rect.bottom()
                                left = 0
                                right = max(0, self.viewport().width() - 1)
                                painter.drawLine(left, y, right, y)
                                painter.end()
                except Exception:
                    pass

        self.tree = ReorderableTreeWidget()
        self.tree.setColumnCount(len(columns))
        self.tree.setHeaderLabels(columns)
        # Set header text alignment
        header_item = self.tree.headerItem()
        for col, col_name in enumerate(columns):
            if col_name in ["Instance", "kgm", "ID", "W", "L", "Corners"]:
                header_item.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            else:
                header_item.setTextAlignment(col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Set resize mode to Interactive so columns can be manually resized by dragging
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Set initial column widths for better fit
        if "Instance" in columns:
            idx = columns.index("Instance")
            self.tree.header().resizeSection(idx, 70)  # Wide enough to show full "Instance" header
        if "kgm" in columns:
            idx = columns.index("kgm")
            self.tree.header().resizeSection(idx, 45)  # Compact for kgm
        if "ID" in columns:
            idx = columns.index("ID")
            self.tree.header().resizeSection(idx, 45)  # Smaller for ID
        if "W" in columns:
            idx = columns.index("W")
            self.tree.header().resizeSection(idx, 45)  # Smaller for W
        if "L" in columns:
            idx = columns.index("L")
            self.tree.header().resizeSection(idx, 45)  # Smaller for L
        if "Corners" in columns:
            idx = columns.index("Corners")
            self.tree.header().resizeSection(idx, 50)  # Compact width for Corners
        self.tree.setTabKeyNavigation(False)  # Disable default row-wise tab behavior
        # Allow multiple selection and enable drag & drop. We handle moves in
        # dropEvent and use startDrag to ensure external drops don't remove
        # sources automatically.
        try:
            # Disable drag & drop to avoid accidental deletion during buggy
            # drag interactions. Use the Move Up/Down buttons for reliable
            # reordering.
            self.tree.setDragEnabled(False)
        except Exception:
            pass
        try:
            self.tree.setAcceptDrops(False)
        except Exception:
            pass
        try:
            self.tree.setDropIndicatorShown(False)
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QAbstractItemView
            self.tree.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        except Exception:
            pass

        # Remove the left indentation and tree decorations so text sits flush to the left
        try:
            # No expand/collapse decoration for top-level rows and no indentation
            self.tree.setRootIsDecorated(False)
            self.tree.setIndentation(0)
        except Exception:
            pass
        # Use Qt's built-in alternating row colors for robust painting
        try:
            self.tree.setAlternatingRowColors(True)
            pal = self.tree.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("white"))
            pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
            self.tree.setPalette(pal)
        except Exception:
            pass
        # Ensure header text is left aligned
        try:
            self.tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        except Exception:
            pass
        # Remove default item padding so cell text is flush to the left edge
        try:
            # apply to QTreeView (QTreeWidget is a subclass)
            self.tree.setStyleSheet("QTreeView::item { padding-left: 0px; padding-top: 2px; padding-bottom: 2px; }")
        except Exception:
            pass

        # Connect itemClicked signal for corner selection
        if self.corners_column_index >= 0:
            self.tree.itemClicked.connect(self.on_tree_item_clicked)

        # Enable right-click context menu for copy/paste corners
        if self.corners_column_index >= 0:
            self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
            self._copied_corners_data = None  # Clipboard for corners copy/paste

        container_layout.addWidget(self.tree)

        # Button panel
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.add_button.clicked.connect(self.add_row)
        button_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("-")
        self.delete_button.clicked.connect(self.delete_row)
        button_layout.addWidget(self.delete_button)

        # Move up / move down buttons for reliable reordering
        self.move_up_button = QPushButton("▲")
        self.move_up_button.setToolTip("Move selected row(s) up\nShortcut: Ctrl+Up")
        self.move_up_button.clicked.connect(self.move_row_up)
        button_layout.addWidget(self.move_up_button)

        self.move_down_button = QPushButton("▼")
        self.move_down_button.setToolTip("Move selected row(s) down\nShortcut: Ctrl+Down")
        self.move_down_button.clicked.connect(self.move_row_down)
        button_layout.addWidget(self.move_down_button)

        # Use a shorter label so the button remains readable at narrow widths
        self.enable_disable_button = QPushButton("Toggle")
        self.enable_disable_button.setToolTip("Enable or disable selected row(s)")
        try:
            # Keep the sizing simple: let the layout size this button like the others.
            from PyQt6.QtWidgets import QSizePolicy
            self.enable_disable_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            # Remove any custom stylesheet so appearance matches other buttons
            try:
                self.enable_disable_button.setStyleSheet("")
            except Exception:
                pass
        except Exception:
            pass
        self.enable_disable_button.clicked.connect(self.toggle_enable_disable_row)
        button_layout.addWidget(self.enable_disable_button)

        # Only create the plot button if a label was provided. This allows
        # callers to suppress the button by passing None/'' for
        # `plot_button_text` (used for expression editor / constraint editor).
        if self.plot_button_text:
            self.plot_button = QPushButton(self.plot_button_text)
            if self.plot_command is not None:
                self.plot_button.clicked.connect(self.plot_command)
            else:
                self.plot_button.clicked.connect(self.plot_row)
            button_layout.addWidget(self.plot_button)
        else:
            self.plot_button = None

        container_layout.addLayout(button_layout)

        # Keep toolbar buttons consistent: give them the same size policy so
        # layouts size them naturally (no forced min widths to avoid overflow).
        try:
            from PyQt6.QtWidgets import QSizePolicy
            btns = [self.add_button, self.delete_button, self.move_up_button, self.move_down_button, self.enable_disable_button]
            if getattr(self, 'plot_button', None):
                btns.append(self.plot_button)
            for b in btns:
                try:
                    b.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                    # Remove any previously set min/max widths so sizing is natural
                    try:
                        b.setMinimumWidth(0)
                        b.setMaximumWidth(16777215)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def add_row(self):
        item = QTreeWidgetItem(["" for _ in self.columns])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make editable
        # Initialize per-item state (not disabled, not plotted)
        try:
            item.setData(0, Qt.ItemDataRole.UserRole, False)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
        except Exception:
            pass
        # Ensure text is aligned properly in each column and vertically centered
        for col in range(len(self.columns)):
            try:
                col_name = self.columns[col]
                if col_name in ["Instance", "kgm", "ID", "W", "L", "Corners"]:
                    item.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            except Exception:
                pass

        self.tree.addTopLevelItem(item)

        # Make the new row obvious: select it, scroll to it, begin editing,
        # and briefly show a horizontal line below the table so the row is obvious.
        try:
            # Select and focus the new item
            self.tree.clearSelection()
            item.setSelected(True)
            self.tree.setCurrentItem(item)
            try:
                # Ensure the item is visible
                self.tree.scrollToItem(item)
            except Exception:
                pass

            # Start editing the first column so the user can immediately type
            try:
                self.tree.editItem(item, 0)
            except Exception:
                pass

            # (No temporary line indicator is used)
        except Exception:
             pass

         # Clear the temporary highlight shortly after adding so alternating
        # colors return to normal; schedule an update to refresh row colors.
        try:
            QTimer.singleShot(1200, self.update_row_colors)
        except Exception:
            try:
                self.update_row_colors()
            except Exception:
                pass

        # Initialize corners to global for new rows
        if self.corners_column_index >= 0:
            self.update_corners_display(item, None)

    def on_tree_item_clicked(self, item, column):
        """Handle clicks on tree items, specifically the Corners column."""
        if column == self.corners_column_index and self.enable_corners:
            self.edit_device_corners(item)

    def _on_tree_context_menu(self, pos):
        """Show right-click context menu with Copy/Paste Corners when clicking the Corners column."""
        item = self.tree.itemAt(pos)
        if item is None:
            return

        # Determine which column was clicked
        header = self.tree.header()
        x = pos.x()
        column = header.logicalIndexAt(x)
        if column != self.corners_column_index:
            return

        menu = QMenu(self)

        copy_action = QAction("Copy Corners", self)
        copy_action.triggered.connect(lambda: self._copy_corners(item))
        menu.addAction(copy_action)

        paste_action = QAction("Paste Corners", self)
        paste_action.setEnabled(self._copied_corners_data is not None)
        paste_action.triggered.connect(lambda: self._paste_corners(item))
        menu.addAction(paste_action)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _copy_corners(self, item):
        """Copy the corners data from the given item to the internal clipboard."""
        import copy as _copy
        corners_data = item.data(self.corners_column_index, Qt.ItemDataRole.UserRole)
        # Deep-copy so later mutations don't affect the clipboard
        self._copied_corners_data = _copy.deepcopy(corners_data)

    def _paste_corners(self, item):
        """Paste the previously copied corners data onto the given item."""
        if self._copied_corners_data is None:
            return
        import copy as _copy
        self.update_corners_display(item, _copy.deepcopy(self._copied_corners_data))

    def get_available_corners(self):
        """Get list of available corners from tech browser."""
        tech_browser = self.tech_browser

        # If tech_browser not set, try to get it dynamically from top_level_app
        if not tech_browser and hasattr(self, '_top_level_app'):
            top_level_app = self._top_level_app
            if top_level_app and hasattr(top_level_app, 'graph_tabs'):
                try:
                    # Try to get the first graph tab
                    first_graph = top_level_app.graph_tabs.widget(0)
                    if first_graph:
                        # Try multiple possible paths to find a lookup window with tech browser
                        if hasattr(first_graph, 'lookup_window_1'):
                            if hasattr(first_graph.lookup_window_1, 'tech_browser'):
                                tech_browser = first_graph.lookup_window_1.tech_browser
                        elif hasattr(first_graph, 'tech_browser'):
                            tech_browser = first_graph.tech_browser
                except Exception as e:
                    print(f"Could not get tech_browser from top_level_app: {e}")

        if not tech_browser:
            return []

        try:
            # Try to get corners from tech browser
            # The tech browser should have a method to get all available corner names
            if hasattr(tech_browser, 'get_all_corner_names'):
                return tech_browser.get_all_corner_names()
            elif hasattr(tech_browser, 'get_checked_paths'):
                # Fallback: extract unique corner names from checked paths
                paths = tech_browser.get_checked_paths()
                corners = set()
                for path in paths:
                    # Path format: "pdk_name/device_type/corner"
                    parts = path.split('/')
                    if len(parts) >= 3:
                        corners.add(parts[2])
                return sorted(list(corners))
        except Exception as e:
            print(f"Error getting available corners: {e}")

        return []

    def edit_device_corners(self, item):
        """Open tech browser window for selecting corners for this device.

        Only one corner-selector window is kept open at a time.  If the window
        is already visible it is reused for the newly-clicked device.
        """
        device_name = item.text(0)  # Get device name from first column

        if not device_name:
            QMessageBox.warning(self, "No Device Name",
                              "Please enter a device name in the Instance column first.")
            return

        # Get tech browser reference
        tech_browser = self.tech_browser
        if not tech_browser and hasattr(self, '_top_level_app'):
            top_level_app = self._top_level_app
            if top_level_app and hasattr(top_level_app, 'graph_tabs'):
                try:
                    first_graph = top_level_app.graph_tabs.widget(0)
                    if first_graph:
                        if hasattr(first_graph, 'lookup_window_1'):
                            if hasattr(first_graph.lookup_window_1, 'tech_browser'):
                                tech_browser = first_graph.lookup_window_1.tech_browser
                        elif hasattr(first_graph, 'tech_browser'):
                            tech_browser = first_graph.tech_browser
                except Exception as e:
                    print(f"Could not get tech_browser: {e}")

        if not tech_browser:
            QMessageBox.information(self, "No Tech Browser Available",
                                  "Tech browser is not available.\n"
                                  "Please open a lookup window with tech browser first.")
            return

        # Get current corners for this item
        current_corners = item.data(self.corners_column_index, Qt.ItemDataRole.UserRole)

        # ------------------------------------------------------------------
        # Single shared window approach: reuse the existing window if open
        # ------------------------------------------------------------------
        if not hasattr(self, '_corner_selector_window'):
            self._corner_selector_window = None
        if not hasattr(self, '_corner_selector_connection'):
            self._corner_selector_connection = None

        window = self._corner_selector_window

        if window is not None and window.isVisible():
            # Disconnect the previous Apply signal so it no longer targets the
            # old item, then reconnect for the new item.
            if self._corner_selector_connection is not None:
                try:
                    window.corners_selected.disconnect(self._corner_selector_connection)
                except Exception:
                    pass

            window.switch_device(device_name, current_corners)

            # Reconnect signal to the new item
            def on_corners_selected(corners, _item=item):
                self.update_corners_display(_item, corners)

            self._corner_selector_connection = on_corners_selected
            window.corners_selected.connect(on_corners_selected)

            window.raise_()
            window.activateWindow()
            return

        # Create a new corner selector window
        window = DeviceCornerSelectorWindow(
            self,
            device_name,
            tech_browser,
            current_corners
        )

        # Connect the signal to update the display when Apply is clicked
        def on_corners_selected(corners, _item=item):
            self.update_corners_display(_item, corners)

        self._corner_selector_connection = on_corners_selected
        window.corners_selected.connect(on_corners_selected)

        # Store window reference
        self._corner_selector_window = window

        # Clean up when window is closed
        def on_window_closed():
            self._corner_selector_window = None
            self._corner_selector_connection = None

        window.finished.connect(on_window_closed)

        # Show the window (non-modal, stays open)
        window.show()
        window.raise_()
        window.activateWindow()

    def update_corners_display(self, item, corner_info):
        """Update the display text and data for corners in an item.

        Args:
            item: Tree widget item
            corner_info: None (global) or list of dicts with corner metadata
        """
        if self.corners_column_index < 0:
            return

        # Store the full corner information (list of dicts with path/pdk/model/length)
        item.setData(self.corners_column_index, Qt.ItemDataRole.UserRole, corner_info)

        # Update display text (show only corner names)
        if corner_info is None:
            # Global - use italic gray
            item.setText(self.corners_column_index, "[*Global*]")
            item.setForeground(self.corners_column_index, QBrush(QColor("gray")))
            font = item.font(self.corners_column_index)
            font.setItalic(True)
            item.setFont(self.corners_column_index, font)
        elif not corner_info:
            # Empty list - error state
            item.setText(self.corners_column_index, "[None]")
            item.setForeground(self.corners_column_index, QBrush(QColor("red")))
            font = item.font(self.corners_column_index)
            font.setItalic(False)
            item.setFont(self.corners_column_index, font)
        else:
            # Custom corner list - extract just the names for display
            corner_names = [c['name'] if isinstance(c, dict) else c for c in corner_info]
            corner_text = ", ".join(corner_names)
            item.setText(self.corners_column_index, f"[{corner_text}]")
            item.setForeground(self.corners_column_index, QBrush(QColor("black")))
            font = item.font(self.corners_column_index)
            font.setItalic(False)
            item.setFont(self.corners_column_index, font)

    def delete_row(self):
        selected_items = self.tree.selectedItems()
        indices_to_remove = sorted([self.tree.indexOfTopLevelItem(item) for item in selected_items], reverse=True)
        for index in indices_to_remove:
            self.tree.takeTopLevelItem(index)

        # No index-based state to recompute (state is stored on items themselves)
        self.update_row_colors()  # Recompute colors after deletion

    def move_row_up(self):
        # Stable move: move each selected row up by one position, preserving
        # relative order and avoiding index-shift issues by rebuilding the
        # tree from a saved snapshot of rows.
        count = self.tree.topLevelItemCount()
        if count == 0:
            return
        selected_indices = sorted({self.tree.indexOfTopLevelItem(it) for it in self.tree.selectedItems()})
        if not selected_indices:
            return

        # Build a snapshot of current rows
        rows = []
        for i in range(count):
            it = self.tree.topLevelItem(i)
            row = {
                'texts': [it.text(c) for c in range(self.tree.columnCount())],
                'user0': it.data(0, Qt.ItemDataRole.UserRole),
                'user1': it.data(0, Qt.ItemDataRole.UserRole + 1),
                'bg': [it.data(c, Qt.ItemDataRole.BackgroundRole) for c in range(self.tree.columnCount())],
                'flags': it.flags(),
                'align': [it.textAlignment(c) for c in range(self.tree.columnCount())],
                'corners': it.data(self.corners_column_index, Qt.ItemDataRole.UserRole) if self.corners_column_index >= 0 else None,
            }
            rows.append(row)

        sel_set = set(selected_indices)
        # Create an order list [0..count-1]
        order = list(range(count))
        # For moving up, scan from 0..n-1 and swap an element with previous if
        # it's selected and previous is not selected.
        for i in range(1, count):
            if order[i] in sel_set and order[i-1] not in sel_set:
                order[i-1], order[i] = order[i], order[i-1]

        # Rebuild tree according to new order and track new positions of selected items
        selected_new_positions = set()
        self.tree.clear()
        for new_idx, orig_idx in enumerate(order):
            # Track if this original index was selected
            if orig_idx in sel_set:
                selected_new_positions.add(new_idx)

            r = rows[orig_idx]
            item = QTreeWidgetItem(r['texts'])
            try:
                item.setFlags(r['flags'])
            except Exception:
                pass
            for c in range(self.tree.columnCount()):
                try:
                    item.setData(c, Qt.ItemDataRole.UserRole, r.get('user0', False))
                except Exception:
                    pass
                try:
                    item.setData(c, Qt.ItemDataRole.UserRole + 1, r.get('user1', False))
                except Exception:
                    pass
                try:
                    item.setData(c, Qt.ItemDataRole.BackgroundRole, r['bg'][c])
                except Exception:
                    pass
                try:
                    item.setTextAlignment(c, r['align'][c])
                except Exception:
                    pass
            # Restore corners data if corners column exists
            if self.corners_column_index >= 0 and 'corners' in r:
                self.update_corners_display(item, r['corners'])
            self.tree.addTopLevelItem(item)

        # Reselect moved items at their new positions
        for idx in selected_new_positions:
            it = self.tree.topLevelItem(idx)
            if it:
                it.setSelected(True)

        # Set the current item to the first selected item for keyboard navigation
        if selected_new_positions:
            first_selected_idx = min(selected_new_positions)
            first_item = self.tree.topLevelItem(first_selected_idx)
            if first_item:
                self.tree.setCurrentItem(first_item)

        self.update_row_colors()

    def move_row_down(self):
        # Stable move down: similar snapshot approach as move_row_up.
        count = self.tree.topLevelItemCount()
        if count == 0:
            return
        selected_indices = sorted({self.tree.indexOfTopLevelItem(it) for it in self.tree.selectedItems()})
        if not selected_indices:
            return

        # Build a snapshot of current rows
        rows = []
        for i in range(count):
            it = self.tree.topLevelItem(i)
            row = {
                'texts': [it.text(c) for c in range(self.tree.columnCount())],
                'user0': it.data(0, Qt.ItemDataRole.UserRole),
                'user1': it.data(0, Qt.ItemDataRole.UserRole + 1),
                'bg': [it.data(c, Qt.ItemDataRole.BackgroundRole) for c in range(self.tree.columnCount())],
                'flags': it.flags(),
                'align': [it.textAlignment(c) for c in range(self.tree.columnCount())],
                'corners': it.data(self.corners_column_index, Qt.ItemDataRole.UserRole) if self.corners_column_index >= 0 else None,
            }
            rows.append(row)

        sel_set = set(selected_indices)
        order = list(range(count))
        # For moving down, scan from n-2 down to 0 and swap element with next
        # if it's selected and next is not selected.
        for i in range(count - 2, -1, -1):
            if order[i] in sel_set and order[i+1] not in sel_set:
                order[i], order[i+1] = order[i+1], order[i]

        # Rebuild tree according to new order and track new positions of selected items
        selected_new_positions = set()
        self.tree.clear()
        for new_idx, orig_idx in enumerate(order):
            # Track if this original index was selected
            if orig_idx in sel_set:
                selected_new_positions.add(new_idx)

            r = rows[orig_idx]
            item = QTreeWidgetItem(r['texts'])
            try:
                item.setFlags(r['flags'])
            except Exception:
                pass
            for c in range(self.tree.columnCount()):
                try:
                    item.setData(c, Qt.ItemDataRole.UserRole, r.get('user0', False))
                except Exception:
                    pass
                try:
                    item.setData(c, Qt.ItemDataRole.UserRole + 1, r.get('user1', False))
                except Exception:
                    pass
                try:
                    item.setData(c, Qt.ItemDataRole.BackgroundRole, r['bg'][c])
                except Exception:
                    pass
                try:
                    item.setTextAlignment(c, r['align'][c])
                except Exception:
                    pass
            # Restore corners data if corners column exists
            if self.corners_column_index >= 0 and 'corners' in r:
                self.update_corners_display(item, r['corners'])
            self.tree.addTopLevelItem(item)

        # Reselect moved items at their new positions
        for idx in selected_new_positions:
            it = self.tree.topLevelItem(idx)
            if it:
                it.setSelected(True)

        # Set the current item to the first selected item for keyboard navigation
        if selected_new_positions:
            first_selected_idx = min(selected_new_positions)
            first_item = self.tree.topLevelItem(first_selected_idx)
            if first_item:
                self.tree.setCurrentItem(first_item)

        self.update_row_colors()

    def toggle_enable_disable_row(self):
        selected_items = self.tree.selectedItems()
        for item in selected_items:
            # Toggle per-item disabled flag stored in UserRole
            try:
                cur = item.data(0, Qt.ItemDataRole.UserRole)
            except Exception:
                cur = False
            new_state = not bool(cur)
            try:
                item.setData(0, Qt.ItemDataRole.UserRole, new_state)
            except Exception:
                pass
            # Update editable flag based on state
            if new_state:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

        self.update_row_colors()  # Ensure colors stay correct

    def update_row_colors(self):
        """Ensures that rows alternate colors correctly after add/delete."""
        # For disabled rows we set a red background; for all other rows
        # clear any explicit background so Qt's alternating row painting is visible.
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            # Read per-item disabled flag stored in UserRole
            try:
                disabled = bool(item.data(0, Qt.ItemDataRole.UserRole))
            except Exception:
                disabled = False
            for col in range(len(self.columns)):
                try:
                    if disabled:
                        item.setData(col, Qt.ItemDataRole.BackgroundRole, QBrush(QColor("#d77f7f")))
                    else:
                        # Clear explicit background so alternating rows show
                        item.setData(col, Qt.ItemDataRole.BackgroundRole, None)
                except Exception:
                    # Fallback to setting/clearing via setBackground if setData isn't supported
                    try:
                        if disabled:
                            item.setBackground(col, QBrush(QColor("#d77f7f")))
                        else:
                            item.setBackground(col, QBrush())
                    except Exception:
                        pass

        # Force a viewport repaint so the alternating row colors are applied immediately
        try:
            self.tree.viewport().update()
            # A slightly deferred repaint helps on some platforms where the model
            # finishing its internal move happens just after our call.
            QTimer.singleShot(20, lambda: (self.tree.viewport().update(), self.tree.update()))
        except Exception:
            pass

    def clear_error_highlights(self):
        """Remove any error-highlighting backgrounds, restoring normal row colours."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            # Remove the error tooltip
            for col in range(self.tree.columnCount()):
                try:
                    item.setToolTip(col, "")
                except Exception:
                    pass
        # Let the normal disabled/alternating colour logic take over
        self.update_row_colors()

    def highlight_error_rows(self, error_symbols):
        """Highlight rows whose symbol (column 0) appears in *error_symbols*.

        Args:
            error_symbols: dict mapping symbol name → error message string.
        """
        if not error_symbols:
            return
        error_bg = QBrush(QColor("#FFB347"))   # orange highlight
        error_fg = QColor("#7B3F00")           # dark brown text
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            sym = item.text(0)
            if sym in error_symbols:
                for col in range(self.tree.columnCount()):
                    try:
                        item.setData(col, Qt.ItemDataRole.BackgroundRole, error_bg)
                        item.setForeground(col, QBrush(error_fg))
                    except Exception:
                        pass
                    try:
                        item.setToolTip(col, f"⚠ Syntax Error: {error_symbols[sym]}")
                    except Exception:
                        pass
        try:
            self.tree.viewport().update()
        except Exception:
            pass

    def get_table_data(self):
        data = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            row_data = {self.columns[j]: item.text(j) for j in range(len(self.columns))}
            try:
                row_data["disabled"] = bool(item.data(0, Qt.ItemDataRole.UserRole))
            except Exception:
                row_data["disabled"] = False
            try:
                row_data["plot"] = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
            except Exception:
                row_data["plot"] = False
            # Save corner data if corners column exists
            if self.corners_column_index >= 0:
                try:
                    corners_data = item.data(self.corners_column_index, Qt.ItemDataRole.UserRole)
                    row_data["_corners_data"] = corners_data  # Use special key to store corner data
                except Exception:
                    row_data["_corners_data"] = None
            data.append(row_data)
        return data

    def load_table_data(self, data):
        self.tree.clear()
        #self.disabled_rows.clear()
        #self.enabled_plot_rows.clear()
        for row_data in data:
            item = QTreeWidgetItem([row_data.get(col, "") for col in self.columns])
            # Ensure editable by default or disabled per data
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            # Initialize per-item state
            try:
                disabled_flag = bool(row_data.get("disabled", False))
                plot_flag = bool(row_data.get("plot", False))
                item.setData(0, Qt.ItemDataRole.UserRole, disabled_flag)
                item.setData(0, Qt.ItemDataRole.UserRole + 1, plot_flag)
            except Exception:
                pass
            # If disabled, remove editable flag
            if row_data.get("disabled"):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Ensure text alignment is proper for each column
            for col in range(len(self.columns)):
                try:
                    col_name = self.columns[col]
                    if col_name in ["Instance", "kgm", "ID", "W", "L", "Corners"]:
                        item.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    else:
                        item.setTextAlignment(col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                except Exception:
                    pass
            # Restore corner data if available
            if self.corners_column_index >= 0 and "_corners_data" in row_data:
                corners_data = row_data.get("_corners_data")
                self.update_corners_display(item, corners_data)
            elif self.corners_column_index >= 0:
                # Initialize to global if no data
                self.update_corners_display(item, None)
            self.tree.addTopLevelItem(item)

        self.update_row_colors()  # Apply correct colors after loading data

    def plot_row(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No item selected", "Please select an item to plot.")
            return

        # In ROAREditorWindow, this will be overridden
        print("Plotting row:", [selected_items[0].text(i) for i in range(self.tree.columnCount())])


class ROAREditorWindow(QWidget):
    expressions_changed = pyqtSignal(list)

    def __init__(self, top_level_app=None):
        super().__init__()
        self.setWindowTitle("Editor Window")
        self.top_level_app = top_level_app
        # Snapping behavior configuration
        # When the window width reaches this fraction of the available
        # parent/screen width, the editor will "snap" to fill horizontally.
        # Set between 0.0 and 1.0. Default 0.75 (75%).
        # Increase the snap threshold so the window has to be very large before snapping
        # (0.0 - 1.0). Setting near 1.0 makes snapping happen only when the editor
        # is almost the full available width.
        #self._snap_threshold_ratio = 0.995
        # Use a more forgiving snap threshold so snapping happens later but not only
        # at near-total width. 0.90 means snap when the editor is >90% of available width.
        self._snap_threshold_ratio = 0.90
        self._snapped = False

        # Make the editor skinnier by default: set a reasonable minimum size
        # and start the window at that minimum so the editor opens compact.
        # Tweak these values if you want a different compact size.
        try:
            # Make the editor narrower by default so it starts compact but usable.
            # Width accommodates instance table columns and Corner Mapping button
            self.setMinimumSize(380, 300)
        except Exception:
            pass
        try:
            # Start the window at the minimum size so the editor opens compact.
            self.resize(self.minimumSize())
        except Exception:
            pass

        layout = QVBoxLayout()
        # COPILOT EDITS
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # END OF COPILOT EDITS
        self.setLayout(layout)

        splitter = QSplitter(Qt.Orientation.Vertical)  # Create a vertical splitter

        # Create editors without plot buttons for Expression and Constraint
        self.expression_editor = BaseEditor("Expression Editor", ["Symbol", "Expression"], plot_button_text=None)
        self.constraint_editor = BaseEditor("Constraint Editor", ["Symbol", "Constraint Expression"], plot_button_text=None)

        # Create instance table WITH corners column and corner selection enabled
        # We'll set the tech_browser reference later when it's available
        self.instance_table = BaseEditor(
            "Instance Table",
            ["Instance", "kgm", "ID", "W", "L", "Corners"],  # Corners column stores both names and full paths
            plot_button_text=None,
            tech_browser=None,  # Will be set dynamically via get_tech_browser()
            enable_corners=True  # Enable corner selection for Design Eqs mode
        )

        # Store reference to top_level_app so we can get tech_browser dynamically
        self.instance_table._top_level_app = top_level_app

        splitter.addWidget(self.expression_editor)
        splitter.addWidget(self.constraint_editor)
        splitter.addWidget(self.instance_table)

        layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refresh all Design Eqs graphs - re-evaluate equations and constraints")
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        self.save_button = QPushButton("Save")
        # Match refresh button size exactly to the Save button's natural size
        self.refresh_button.setFixedSize(28, self.save_button.sizeHint().height())
        self.open_editor_button = QPushButton("Open Editor")
        self.corner_mapping_button = QPushButton("Corner Map")
        self.corner_mapping_button.setToolTip(
            "View and configure device corner mappings for 3D plotting.\n"
            "Ensures all devices use compatible corner sets."
        )
        self.corner_mapping_button.clicked.connect(self.show_corner_mapping_dialog)

        self.save_button.clicked.connect(self.save_all_data)

        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_all_data)

        button_layout.addWidget(self.corner_mapping_button)
        button_layout.addWidget(self.open_editor_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        # Connect signals for expression changes
        self.expression_editor.tree.itemChanged.connect(self.on_expressions_changed)
        self.expression_editor.add_button.clicked.connect(self.on_expressions_changed)
        self.expression_editor.delete_button.clicked.connect(self.on_expressions_changed)
        self.expression_editor.enable_disable_button.clicked.connect(self.on_expressions_changed)  # Update when toggling enable/disable

        # Connect the open editor button to toggle dock/undock
        self.open_editor_button.clicked.connect(self.toggle_dock_undock)

        # Initialize dock state
        self.is_docked = True
        self.original_parent = None
        self.original_index = -1

        # Debounce timer for expression changes to prevent lag
        self._expressions_changed_timer = QTimer()
        self._expressions_changed_timer.setSingleShot(True)
        self._expressions_changed_timer.setInterval(300)  # 300ms debounce
        self._expressions_changed_timer.timeout.connect(self._emit_expressions_changed)

    def on_expressions_changed(self):
        """Debounced handler for expression changes - starts/restarts timer."""
        # Restart the timer on each change - only emit after user stops editing for 300ms
        self._expressions_changed_timer.start()

    def _emit_expressions_changed(self):
        """Actually emit the expressions_changed signal after debounce delay."""
        self.expressions_changed.emit(self.get_expression_symbols())

    def get_expression_symbols(self):
        symbols = []
        for i in range(self.expression_editor.tree.topLevelItemCount()):
            item = self.expression_editor.tree.topLevelItem(i)
            # Check if the row is disabled (UserRole data is True for disabled rows)
            try:
                disabled = bool(item.data(0, Qt.ItemDataRole.UserRole))
            except Exception:
                disabled = False

            # Skip disabled expressions
            if disabled:
                continue

            symbol = item.text(0)
            if symbol:
                symbols.append(symbol)
        return symbols

    def get_expressions_and_constraints(self):
        expressions = {}
        for i in range(self.expression_editor.tree.topLevelItemCount()):
            item = self.expression_editor.tree.topLevelItem(i)
            # Check if the row is disabled (UserRole data is True for disabled rows)
            try:
                disabled = bool(item.data(0, Qt.ItemDataRole.UserRole))
            except Exception:
                disabled = False

            # Skip disabled expressions
            if disabled:
                continue

            symbol = item.text(0)
            expr = item.text(1)
            if symbol:
                expressions[symbol] = expr

        constraints = {}
        for i in range(self.constraint_editor.tree.topLevelItemCount()):
            item = self.constraint_editor.tree.topLevelItem(i)
            # Check if the row is disabled
            try:
                disabled = bool(item.data(0, Qt.ItemDataRole.UserRole))
            except Exception:
                disabled = False

            # Skip disabled constraints
            if disabled:
                continue

            symbol = item.text(0)
            constraint_expr = item.text(1)
            if symbol:
                constraints[symbol] = constraint_expr

        return expressions, constraints

    def get_device_corners(self):
        """Get dictionary mapping device names to their corner selections and device info.

        Returns:
            dict: {device_name: {
                'corners': list of corner names or None (None means use global),
                'corner_paths': list of full corner paths,
                'pdk': pdk_name (extracted from first corner, or None),
                'model': model_name (extracted from first corner, or None),
                'length': length_value (extracted from first corner, or None)
            }}
        """
        device_corners = {}
        corners_column_index = self.instance_table.corners_column_index

        if corners_column_index < 0:
            # No corners column, return empty dict
            return device_corners

        for i in range(self.instance_table.tree.topLevelItemCount()):
            item = self.instance_table.tree.topLevelItem(i)
            device_name = item.text(0)  # Instance column
            if device_name:
                # Get corner data from UserRole (now a list of dicts with path info)
                corner_info = item.data(corners_column_index, Qt.ItemDataRole.UserRole)

                if corner_info is None:
                    # Global selection
                    device_corners[device_name] = {
                        'corners': None,
                        'corner_paths': None,
                        'pdk': None,
                        'model': None,
                        'length': None
                    }
                elif isinstance(corner_info, list) and len(corner_info) > 0:
                    # Device-specific corners with metadata
                    # Extract corner names and paths
                    corner_names = []
                    corner_paths = []
                    pdk = None
                    model = None
                    length = None

                    for c in corner_info:
                        if isinstance(c, dict):
                            corner_names.append(c.get('name', ''))
                            corner_paths.append(c.get('path', ''))
                            # Use first corner's metadata for device info
                            if pdk is None:
                                pdk = c.get('pdk')
                                model = c.get('model')
                                length = c.get('length')
                        else:
                            # Old format - just corner name strings
                            corner_names.append(c)

                    device_corners[device_name] = {
                        'corners': corner_names if corner_names else None,
                        'corner_paths': corner_paths if corner_paths else None,
                        'pdk': pdk,
                        'model': model,
                        'length': length
                    }
                else:
                    # Empty or unknown format
                    device_corners[device_name] = {
                        'corners': None,
                        'corner_paths': None,
                        'pdk': None,
                        'model': None,
                        'length': None
                    }

        return device_corners

    # ------------------------------------------------------------------
    # Expression / constraint validation
    # ------------------------------------------------------------------
    def validate_expressions(self):
        """Parse all expressions and constraints through the equation solver.

        Returns:
            dict: ``{symbol: error_message}`` for every entry that has a
                  syntax or parse error.  Empty dict means everything is OK.
        """
        try:
            from .equation_solver import ROAREquationSolver
        except ImportError:
            try:
                from equation_solver import ROAREquationSolver
            except ImportError:
                return {}

        errors = {}
        expressions, constraints = self.get_expressions_and_constraints()
        solver = ROAREquationSolver(top_level_app=self.top_level_app)

        for sym, expr in expressions.items():
            err = solver.add_equation(sym, expr)
            if err:
                errors[sym] = err

        for sym, expr in constraints.items():
            err = solver.add_equation(sym, expr)
            if err:
                errors[sym] = err

        return errors

    def on_refresh_clicked(self):
        """Refresh all Design Eqs graphs by re-evaluating equations and constraints.

        This is the single trigger point for refreshing design equation graphs.
        It updates expression symbols and triggers graph updates for all lookup
        windows that are in Design Eqs mode.
        """
        if not self.top_level_app:
            return

        # ── Validate first ──
        # Clear any previous error highlights
        self.expression_editor.clear_error_highlights()
        self.constraint_editor.clear_error_highlights()

        errors = self.validate_expressions()
        if errors:
            # Separate expression vs constraint errors
            expressions, constraints = self.get_expressions_and_constraints()
            expr_errors = {s: m for s, m in errors.items() if s in expressions}
            cons_errors = {s: m for s, m in errors.items() if s in constraints}

            # Highlight offending rows
            if expr_errors:
                self.expression_editor.highlight_error_rows(expr_errors)
            if cons_errors:
                self.constraint_editor.highlight_error_rows(cons_errors)

            # Build user-friendly message
            lines = []
            for sym, msg in errors.items():
                # Truncate long error messages
                short = (msg[:120] + "…") if len(msg) > 120 else msg
                lines.append(f"  • {sym}:  {short}")
            detail = "\n".join(lines)

            QMessageBox.warning(
                self,
                "Syntax Errors in Design Equations",
                f"{len(errors)} expression(s) contain syntax errors.\n"
                f"Please fix the highlighted entries before refreshing.\n\n"
                f"{detail}"
            )
            return  # ← do NOT graph anything

        # Create progress dialog
        progress = QProgressDialog("Refreshing Design Equations...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Refresh Progress")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately
        progress.setValue(0)
        progress.setMinimumWidth(350)
        QApplication.processEvents()

        try:
            # Step 1: Get expression symbols (10%)
            progress.setLabelText("Reading expressions...")
            progress.setValue(5)
            QApplication.processEvents()
            if progress.wasCanceled():
                return

            symbols = self.get_expression_symbols()
            progress.setValue(10)
            QApplication.processEvents()

            # Step 2: Find all lookup windows (20%)
            progress.setLabelText("Finding graph windows...")
            QApplication.processEvents()
            if progress.wasCanceled():
                return

            lookup_windows = []

            # Check graph_grid structure (multiple pane layouts)
            if hasattr(self.top_level_app, 'graph_grid'):
                grid = self.top_level_app.graph_grid
                for attr_name in dir(grid):
                    if 'lookup_window' in attr_name.lower():
                        try:
                            lw = getattr(grid, attr_name, None)
                            if lw is not None and hasattr(lw, 'is_device_params_mode'):
                                lookup_windows.append(lw)
                        except Exception:
                            pass

            # Check graph_tabs structure (tabbed layouts)
            if hasattr(self.top_level_app, 'graph_tabs'):
                try:
                    tabs = self.top_level_app.graph_tabs
                    for i in range(tabs.count()):
                        widget = tabs.widget(i)
                        if widget is not None:
                            if hasattr(widget, 'is_device_params_mode'):
                                lookup_windows.append(widget)
                            for attr_name in dir(widget):
                                if 'lookup_window' in attr_name.lower():
                                    try:
                                        lw = getattr(widget, attr_name, None)
                                        if lw is not None and hasattr(lw, 'is_device_params_mode'):
                                            if lw not in lookup_windows:
                                                lookup_windows.append(lw)
                                    except Exception:
                                        pass
                except Exception:
                    pass

            # Check for single lookup_window attribute
            if hasattr(self.top_level_app, 'lookup_window'):
                try:
                    lw = self.top_level_app.lookup_window
                    if lw is not None and hasattr(lw, 'is_device_params_mode'):
                        if lw not in lookup_windows:
                            lookup_windows.append(lw)
                except Exception:
                    pass

            progress.setValue(20)
            QApplication.processEvents()

            # Step 3: Filter to Design Eqs mode windows
            design_eq_windows = [lw for lw in lookup_windows
                                 if hasattr(lw, 'is_device_params_mode') and not lw.is_device_params_mode]

            if not design_eq_windows:
                progress.setLabelText("No Design Eqs windows to refresh.")
                progress.setValue(100)
                QApplication.processEvents()
                return

            # Step 4: Update each window (20% to 100%)
            num_windows = len(design_eq_windows)
            progress_per_window = 80 // max(num_windows, 1)

            for idx, lw in enumerate(design_eq_windows):
                if progress.wasCanceled():
                    return

                window_name = f"Window {idx + 1}/{num_windows}"

                # Update expression symbols
                progress.setLabelText(f"{window_name}: Updating expression symbols...")
                progress.setValue(20 + idx * progress_per_window)
                QApplication.processEvents()

                try:
                    if hasattr(lw, 'expression_symbols'):
                        lw.expression_symbols = symbols
                    if hasattr(lw, 'update_combobox_items'):
                        lw.update_combobox_items()
                except Exception:
                    pass

                if progress.wasCanceled():
                    return

                # Evaluate equations and update graph
                progress.setLabelText(f"{window_name}: Evaluating equations and plotting...")
                progress.setValue(20 + idx * progress_per_window + progress_per_window // 2)
                QApplication.processEvents()

                try:
                    if hasattr(lw, 'update_graph_from_tech_browser'):
                        lw.update_graph_from_tech_browser()
                except Exception:
                    pass

            # Complete
            progress.setLabelText("Refresh complete!")
            progress.setValue(100)
            QApplication.processEvents()

        except Exception as e:
            progress.close()
            QMessageBox.warning(self, "Refresh Error", f"An error occurred during refresh:\n{str(e)}")
            return

        progress.close()

    def show_corner_mapping_dialog(self):
        """Show the corner mapping dialog for 3D plotting configuration."""
        try:
            from .corner_mapping_dialog import CornerMappingDialog
        except ImportError:
            try:
                from corner_mapping_dialog import CornerMappingDialog
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Feature Not Available",
                    "Corner Mapping dialog could not be loaded."
                )
                return

        # Get tech browser reference
        tech_browser = None
        if hasattr(self, 'get_tech_browser'):
            tech_browser = self.get_tech_browser()
        elif hasattr(self, 'top_level_app') and self.top_level_app:
            # Try to get from first lookup window
            try:
                tech_browser = self.top_level_app.graph_grid.lookup_window_1.tech_browser
            except Exception:
                pass

        if not tech_browser:
            QMessageBox.warning(
                self,
                "Tech Browser Not Found",
                "Could not find tech browser reference.\n"
                "The corner mapping dialog requires an active tech browser."
            )
            return

        # Create and show dialog (reuse existing to preserve tuple states)
        if not hasattr(self, '_corner_mapping_dialog') or self._corner_mapping_dialog is None:
            dialog = CornerMappingDialog(self, self, tech_browser)

            # Connect signal to refresh design editor if corners changed
            def on_corners_changed():
                # Trigger re-evaluation or update if needed
                if hasattr(self, 'on_expressions_changed'):
                    self.on_expressions_changed()

            dialog.corner_mapping_changed.connect(on_corners_changed)
            self._corner_mapping_dialog = dialog
        else:
            # Reuse the existing dialog (preserves tuple checkbox / color state)
            self._corner_mapping_dialog.tech_browser = tech_browser
            self._corner_mapping_dialog.update_corner_info()

        self._corner_mapping_dialog.exec()

    def plot_expression(self):
        selected_items = self.expression_editor.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Expression Selected", "Please select an expression to graph.")
            return

        selected_item = selected_items[0]
        expression = selected_item.text(1)

        if self.top_level_app:
            # For now, plot on the first graph
            lookup_window = self.top_level_app.graph_grid.lookup_window_1
            lookup_window.plot_custom_equation(expression)

    def save_all_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "JSON Files (*.json)")
        if file_path:
            data = {
                "expression_editor": self.expression_editor.get_table_data(),
                "constraint_editor": self.constraint_editor.get_table_data(),
                "instance_table": self.instance_table.get_table_data()
            }
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)
            QMessageBox.information(self, "Success", "Data saved successfully!")

    def load_all_data(self, file_path=None, show_success_message=True):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "JSON Files (*.json)")

        if file_path:
            try:
                with open(file_path, "r") as file:
                    data = json.load(file)
                self.expression_editor.load_table_data(data.get("expression_editor", []))
                self.constraint_editor.load_table_data(data.get("constraint_editor", []))
                self.instance_table.load_table_data(data.get("instance_table", []))
                if show_success_message:
                    QMessageBox.information(self, "Success", "Data loaded successfully!")

                # Emit signal after loading data
                self.on_expressions_changed()
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", f"File not found: {file_path}")
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", f"Error decoding JSON from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Get the available width from the parent or screen
        available_width = self.parent().width() if self.parent() else QApplication.primaryScreen().availableGeometry().width()

        # Calculate the threshold width for snapping
        threshold_width = available_width * self._snap_threshold_ratio

        if self.width() > threshold_width and not self._snapped:
            # Snap to fill the available width
            new_width = available_width
            self.resize(new_width, self.height())
            self._snapped = True
        elif self.width() <= threshold_width and self._snapped:
            # Unsnap if the window is resized smaller than the threshold
            self._snapped = False

    def set_snap_threshold_ratio(self, ratio: float):
        """Set the snap threshold ratio (0.0 - 1.0). When the editor width
        exceeds available_width * ratio it will snap to fill the available width.
        """
        try:
            r = float(ratio)
        except Exception:
            return
        if r < 0.0:
            r = 0.0
        if r > 1.0:
            r = 1.0
        self._snap_threshold_ratio = r

    def toggle_dock_undock(self):
        """Toggle between docked and undocked states of the editor window."""
        if self.is_docked:
            self.undock_editor()
        else:
            self.dock_editor()

    def undock_editor(self):
        """Undock the editor to a separate window."""
        if not self.top_level_app:
            return

        # Find the splitter containing this editor
        parent_widget = self.parent()
        if not parent_widget:
            return

        # The parent should be a QSplitter (horizontal splitter with graph tabs)
        if not isinstance(parent_widget, QSplitter):
            return

        # Store original position information
        self.original_parent = parent_widget
        self.original_index = parent_widget.indexOf(self)

        # Remove from splitter
        self.setParent(None)

        # Set window flags for a proper separate window
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("ROAR Design Editor")

        # Set the window icon to match the main application
        try:
            window_icon = QIcon(ROAR_HOME + "/images/png/ROAR_ICON.png")
            self.setWindowIcon(window_icon)
        except Exception:
            pass  # Silently fail if icon can't be loaded

        # Show as separate window
        self.show()
        self.raise_()
        self.activateWindow()

        # Update button text
        self.open_editor_button.setText("Dock Editor")

        # Update dock state
        self.is_docked = False

    def dock_editor(self):
        """Dock the editor back into the main window."""
        if not self.original_parent or self.original_index < 0:
            return

        # Remove window flags first (while still visible)
        self.setWindowFlags(Qt.WindowType.Widget)

        # Re-add to the original splitter at the original position
        self.original_parent.insertWidget(self.original_index, self)

        # Ensure the widget is visible after re-parenting
        self.show()

        # Reset window title (back to embedded state)
        self.setWindowTitle("Editor Window")

        # Update button text
        self.open_editor_button.setText("Open Editor")

        # Update dock state
        self.is_docked = True

        # Clear stored position info
        self.original_parent = None
        self.original_index = -1

    def closeEvent(self, event):
        """Handle the close event when the editor is undocked."""
        if not self.is_docked:
            # If the window is closed while undocked, dock it back
            self.dock_editor()
            event.ignore()  # Don't actually close the window, just dock it
        else:
            # If docked, allow normal closing
            super().closeEvent(event)
