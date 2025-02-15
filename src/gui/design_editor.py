from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QLineEdit,
    QDialog, QLabel, QComboBox, QMessageBox, QSplitter
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import json
import sys
from equation_solver import *
#from gui4 import *


class BaseEditor(QWidget):
    def __init__(self, title, columns, plot_button_text="Add LUT", plot_command=None, add_command=None):
        super().__init__()
        self.columns = columns
        self.plot_button_text = plot_button_text
        self.plot_command = plot_command
        self.disabled_rows = set()
        self.enabled_plot_rows = set()

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create the TreeWidget
        self.tree = QTreeWidget()
        self.tree.setColumnCount(len(columns))
        self.tree.setHeaderLabels(columns)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Allow resizing
        self.tree.setTabKeyNavigation(False)  # Disable default row-wise tab behavior
        layout.addWidget(self.tree)

        # Button panel
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.add_button.clicked.connect(self.add_row)
        button_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("-")
        self.delete_button.clicked.connect(self.delete_row)
        button_layout.addWidget(self.delete_button)

        self.enable_disable_button = QPushButton("Enable/Disable")
        self.enable_disable_button.clicked.connect(self.toggle_enable_disable_row)
        button_layout.addWidget(self.enable_disable_button)

        self.plot_button = QPushButton(self.plot_button_text)
        if self.plot_command is not None:
            self.plot_button.clicked.connect(self.plot_command)
        button_layout.addWidget(self.plot_button)

        layout.addLayout(button_layout)

    def add_row(self):
        item = QTreeWidgetItem(["" for _ in self.columns])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Make editable

        self.tree.addTopLevelItem(item)
        self.update_row_colors()  # Ensure correct alternating colors

    def delete_row(self):
        selected_items = self.tree.selectedItems()
        indices_to_remove = sorted([self.tree.indexOfTopLevelItem(item) for item in selected_items], reverse=True)
        for index in indices_to_remove:
            self.tree.takeTopLevelItem(index)

        # Recalculate disabled row indices
        self.disabled_rows = {i for i in range(self.tree.topLevelItemCount()) if i in self.disabled_rows}

        self.update_row_colors()  # Recompute colors after deletion

    def toggle_enable_disable_row(self):
        selected_items = self.tree.selectedItems()
        for item in selected_items:
            index = self.tree.indexOfTopLevelItem(item)
            if index in self.disabled_rows:
                self.disabled_rows.remove(index)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Enable editing
            else:
                self.disabled_rows.add(index)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Disable editing

        self.update_row_colors()  # Ensure colors stay correct

    def update_row_colors(self):
        """Ensures that rows alternate colors correctly after add/delete."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if i in self.disabled_rows:
                color = QColor("#d77f7f")  # Keep disabled rows red
            else:
                color = QColor("#f0f0f0") if i % 2 == 0 else QColor("white")  # Alternate colors
            for col in range(len(self.columns)):
                item.setBackground(col, color)

    def get_table_data(self):
        data = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            row_data = {self.columns[j]: item.text(j) for j in range(len(self.columns))}
            row_data["disabled"] = i in self.disabled_rows
            row_data["plot"] = i in self.enabled_plot_rows
            data.append(row_data)
        return data

    def load_table_data(self, data):
        self.tree.clear()
        self.disabled_rows.clear()
        self.enabled_plot_rows.clear()
        for row_data in data:
            item = QTreeWidgetItem([row_data[col] for col in self.columns])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)  # Ensure editable by default
            self.tree.addTopLevelItem(item)

            if row_data.get("disabled"):
                self.disabled_rows.add(self.tree.indexOfTopLevelItem(item))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Disable editing
                for col in range(len(self.columns)):
                    item.setBackground(col, QColor("#d77f7f"))

        self.update_row_colors()  # Apply correct colors after loading data


class ROAREditorWindow(QWidget):
    def __init__(self, top_level_app=None):
        super().__init__()
        self.setWindowTitle("Editor Window")
        self.top_level_app = top_level_app
        layout = QVBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter(Qt.Orientation.Vertical)  # Create a vertical splitter

        self.expression_editor = BaseEditor("Expression Editor", ["Symbol", "Expression"])
        self.constraint_editor = BaseEditor("Constraint Editor", ["Symbol", "Constraint Expression"], plot_button_text="Show Constraint")
        self.instance_table = BaseEditor("Instance Table", ["Instance Name", "kgm", "ID", "W", "L"], plot_button_text="Set LUTs")

        splitter.addWidget(self.expression_editor)
        splitter.addWidget(self.constraint_editor)
        splitter.addWidget(self.instance_table)

        layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.evaluate_button = QPushButton("Evaluate")
        self.open_editor_button = QPushButton("Open Editor")
        self.save_button.clicked.connect(self.save_all_data)

        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_all_data)
        button_layout.addWidget(self.evaluate_button)
        button_layout.addWidget(self.open_editor_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

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

    def load_all_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, "r") as file:
                data = json.load(file)
            self.expression_editor.load_table_data(data.get("expression_editor", []))
            self.constraint_editor.load_table_data(data.get("constraint_editor", []))
            self.instance_table.load_table_data(data.get("instance_table", []))
            QMessageBox.information(self, "Success", "Data loaded successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EditorWindow()
    window.show()
    sys.exit(app.exec())
