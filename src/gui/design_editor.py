from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QMessageBox, QSplitter, QGroupBox
)
from PyQt6.QtGui import QColor, QBrush, QPalette, QPainter, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import json
import sys


class BaseEditor(QWidget):
    def __init__(self, title, columns, plot_button_text="Add LUT", plot_command=None, add_command=None):
        super().__init__()
        self.columns = columns
        self.plot_button_text = plot_button_text
        self.plot_command = plot_command
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
            if col_name in ["kgm", "ID", "W", "L"]:
                header_item.setTextAlignment(col, Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            else:
                header_item.setTextAlignment(col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Allow resizing
        # Set initial column widths for better fit
        if "Instance Name" in columns:
            idx = columns.index("Instance Name")
            self.tree.header().resizeSection(idx, 150)  # Wider for Instance Name
        if "kgm" in columns:
            idx = columns.index("kgm")
            self.tree.header().resizeSection(idx, 60)  # Thinner for kgm
        if "ID" in columns:
            idx = columns.index("ID")
            self.tree.header().resizeSection(idx, 60)  # Thinner for ID
        if "W" in columns:
            idx = columns.index("W")
            self.tree.header().resizeSection(idx, 60)  # Thinner for W
        if "L" in columns:
            idx = columns.index("L")
            self.tree.header().resizeSection(idx, 60)  # Thinner for L
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
        # Ensure text is left-aligned in each column and vertically centered
        for col in range(len(self.columns)):
            try:
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

        # Rebuild tree according to new order
        selected_new_positions = set()
        self.tree.clear()
        for new_idx, orig_idx in enumerate(order):
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
            self.tree.addTopLevelItem(item)
            if orig_idx in sel_set:
                selected_new_positions.add(new_idx)

        # Reselect moved items
        for idx in selected_new_positions:
            it = self.tree.topLevelItem(idx)
            if it:
                it.setSelected(True)

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
            }
            rows.append(row)

        sel_set = set(selected_indices)
        order = list(range(count))
        # For moving down, scan from n-2 down to 0 and swap element with next
        # if it's selected and next is not selected.
        for i in range(count - 2, -1, -1):
            if order[i] in sel_set and order[i+1] not in sel_set:
                order[i], order[i+1] = order[i+1], order[i]

        # Rebuild tree according to new order
        selected_new_positions = set()
        self.tree.clear()
        for new_idx, orig_idx in enumerate(order):
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
            self.tree.addTopLevelItem(item)
            if orig_idx in sel_set:
                selected_new_positions.add(new_idx)

        # Reselect moved items
        for idx in selected_new_positions:
            it = self.tree.topLevelItem(idx)
            if it:
                it.setSelected(True)

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
            # Ensure text alignment is flush left for each column
            for col in range(len(self.columns)):
                try:
                    item.setTextAlignment(col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                except Exception:
                    pass
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
            self.setMinimumSize(320, 300)
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
        # Create instance table without the Set LUTs plot button
        self.instance_table = BaseEditor("Instance Table", ["Instance Name", "kgm", "ID", "W", "L"], plot_button_text=None)

        splitter.addWidget(self.expression_editor)
        splitter.addWidget(self.constraint_editor)
        splitter.addWidget(self.instance_table)

        layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.evaluate_button = QPushButton("Evaluate")
        self.open_editor_button = QPushButton("Open Editor")
        # Removed the Plot Equation button per request
        self.save_button.clicked.connect(self.save_all_data)

        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_all_data)
        button_layout.addWidget(self.evaluate_button)
        button_layout.addWidget(self.open_editor_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        # Connect signals for expression changes
        self.expression_editor.tree.itemChanged.connect(self.on_expressions_changed)
        self.expression_editor.add_button.clicked.connect(self.on_expressions_changed)
        self.expression_editor.delete_button.clicked.connect(self.on_expressions_changed)

    def on_expressions_changed(self):
        self.expressions_changed.emit(self.get_expression_symbols())

    def get_expression_symbols(self):
        symbols = []
        for i in range(self.expression_editor.tree.topLevelItemCount()):
            item = self.expression_editor.tree.topLevelItem(i)
            symbol = item.text(0)
            if symbol:
                symbols.append(symbol)
        return symbols

    def get_expressions_and_constraints(self):
        expressions = {}
        for i in range(self.expression_editor.tree.topLevelItemCount()):
            item = self.expression_editor.tree.topLevelItem(i)
            symbol = item.text(0)
            expr = item.text(1)
            if symbol:
                expressions[symbol] = expr

        constraints = {}
        for i in range(self.constraint_editor.tree.topLevelItemCount()):
            item = self.constraint_editor.tree.topLevelItem(i)
            symbol = item.text(0)
            constraint_expr = item.text(1)
            if symbol:
                constraints[symbol] = constraint_expr

        return expressions, constraints

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ROAREditorWindow()
    window.show()
    sys.exit(app.exec())
