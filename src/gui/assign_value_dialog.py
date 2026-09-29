"""Assign a marker readout to an instance-table attribute.

A vertical marker pins one X value shared by every curve, but each selected
corner yields its own Y value.  This dialog makes that collapse explicit: the
user picks which axis to take and how to reduce the per-corner spread to the
single number that a SPICE ``.param`` needs.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QGroupBox, QMessageBox,
    QHeaderView, QAbstractItemView, QCheckBox,
)
from PyQt6.QtCore import Qt

try:
    from .design_editor import format_param_value
except ImportError:
    from design_editor import format_param_value


COMMON_ATTRIBUTES = ["W", "L", "kgm", "ID"]

# Reduction policies collapsing N corner values into the one exported number.
REDUCE_WORST_MAX = "max (worst-case high)"
REDUCE_WORST_MIN = "min (worst-case low)"
REDUCE_MEAN = "mean"
REDUCE_CORNER = "single corner"


class AssignValueDialog(QDialog):
    def __init__(self, parent, instance_table, readouts, vertical=True, axis_names=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Value to Instance")
        self.setMinimumWidth(460)

        self.instance_table = instance_table
        self.readouts = readouts
        self.vertical = vertical
        self.axis_names = axis_names or {"x": "X", "y": "Y"}

        layout = QVBoxLayout(self)

        pinned_axis = "x" if vertical else "y"
        pinned_value = readouts[0][pinned_axis]
        header = QLabel(
            f"<b>{'Vertical' if vertical else 'Horizontal'} marker</b> pinned at "
            f"{self.axis_names[pinned_axis]} = {format_param_value(pinned_value)}"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        layout.addWidget(self._build_corner_table())

        form_box = QGroupBox("Assignment")
        form = QFormLayout(form_box)

        self.instance_combo = QComboBox()
        self.instance_combo.addItems(self.instance_table.get_instance_names())
        if self.instance_combo.count() == 0:
            self.instance_combo.setEnabled(False)
        form.addRow("Instance:", self.instance_combo)

        self.attr_combo = QComboBox()
        self.attr_combo.setEditable(True)
        known = list(COMMON_ATTRIBUTES)
        for col in self.instance_table.columns:
            if col not in ("Instance", "Corners") and col not in known:
                known.append(col)
        self.attr_combo.addItems(known)
        self.attr_combo.setToolTip(
            "Pick an existing column or type a new attribute name."
        )
        form.addRow("Attribute:", self.attr_combo)

        self.add_column_check = QCheckBox("Add as a column in the instance table")
        self.add_column_check.setToolTip(
            "New attributes are stored on the instance either way.\n"
            "Adding a column also shows the value directly in the table."
        )
        form.addRow("", self.add_column_check)
        self.attr_combo.currentTextChanged.connect(self._on_attr_changed)

        self.source_combo = QComboBox()
        self.source_combo.addItem(
            f"{self.axis_names['x']}  (pinned)" if vertical else self.axis_names["x"], "x")
        self.source_combo.addItem(
            self.axis_names["y"] if vertical else f"{self.axis_names['y']}  (pinned)", "y")
        self.source_combo.setCurrentIndex(1 if vertical else 0)
        self.source_combo.currentIndexChanged.connect(self._update_preview)
        form.addRow("Take value from:", self.source_combo)

        self.reduce_combo = QComboBox()
        self.reduce_combo.addItems(
            [REDUCE_WORST_MAX, REDUCE_WORST_MIN, REDUCE_MEAN, REDUCE_CORNER])
        self.reduce_combo.currentIndexChanged.connect(self._on_reduce_changed)
        form.addRow("Across corners:", self.reduce_combo)

        self.corner_combo = QComboBox()
        for entry in readouts:
            self.corner_combo.addItem(entry["corner_name"], entry["curve_idx"])
        self.corner_combo.setEnabled(False)
        self.corner_combo.currentIndexChanged.connect(self._update_preview)
        form.addRow("Corner:", self.corner_combo)

        layout.addWidget(form_box)

        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.preview_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self.assign_button = QPushButton("Assign")
        self.assign_button.setDefault(True)
        self.assign_button.clicked.connect(self._on_assign)
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.assign_button)
        layout.addLayout(buttons)

        self._on_attr_changed(self.attr_combo.currentText())
        self._update_preview()

    def _on_attr_changed(self, text):
        """Offer the column option only for attributes that have no column yet."""
        attr = (text or "").strip()
        is_new = bool(attr) and attr not in self.instance_table.columns
        self.add_column_check.setEnabled(is_new)
        self.add_column_check.setChecked(is_new)
        if not is_new and attr:
            self.add_column_check.setText("Already a column in the instance table")
        else:
            self.add_column_check.setText("Add as a column in the instance table")

    def _build_corner_table(self):
        table = QTableWidget(len(self.readouts), 3)
        table.setHorizontalHeaderLabels(
            ["Corner", self.axis_names["x"], self.axis_names["y"]])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row, entry in enumerate(self.readouts):
            table.setItem(row, 0, QTableWidgetItem(entry["corner_name"]))
            table.setItem(row, 1, QTableWidgetItem(format_param_value(entry["x"])))
            table.setItem(row, 2, QTableWidgetItem(format_param_value(entry["y"])))

        height = min(160, 28 * (len(self.readouts) + 1) + 4)
        table.setMaximumHeight(height)
        return table

    def _on_reduce_changed(self):
        self.corner_combo.setEnabled(
            self.reduce_combo.currentText() == REDUCE_CORNER)
        self._update_preview()

    def _pinned_axis(self):
        return "x" if self.vertical else "y"

    def _resolve(self):
        """Return (value, per_corner_dict, reduce_label)."""
        axis = self.source_combo.currentData()
        per_corner = {e["corner_name"]: e[axis] for e in self.readouts}
        values = [e[axis] for e in self.readouts]

        # The pinned axis is identical across curves, so reduction is a no-op.
        if axis == self._pinned_axis():
            return values[0], per_corner, "pinned"

        mode = self.reduce_combo.currentText()
        if mode == REDUCE_WORST_MAX:
            return max(values), per_corner, mode
        if mode == REDUCE_WORST_MIN:
            return min(values), per_corner, mode
        if mode == REDUCE_MEAN:
            return sum(values) / len(values), per_corner, mode

        idx = self.corner_combo.currentIndex()
        if idx < 0:
            idx = 0
        entry = self.readouts[idx]
        return entry[axis], per_corner, f"corner {entry['corner_name']}"

    def _update_preview(self):
        axis = self.source_combo.currentData()
        is_pinned = axis == self._pinned_axis()
        self.reduce_combo.setEnabled(not is_pinned)
        self.corner_combo.setEnabled(
            not is_pinned and self.reduce_combo.currentText() == REDUCE_CORNER)

        value, _per_corner, reduce_label = self._resolve()
        spread = ""
        if not is_pinned and len(self.readouts) > 1:
            values = [e[axis] for e in self.readouts]
            spread = (f"   (spread {format_param_value(min(values))} … "
                      f"{format_param_value(max(values))})")
        self.preview_label.setText(
            f"Resolved value: {format_param_value(value)}  [{reduce_label}]{spread}")

    def _on_assign(self):
        instance_name = self.instance_combo.currentText().strip()
        if not instance_name:
            QMessageBox.warning(self, "Assign to Instance",
                                "Add an instance to the instance table first.")
            return

        attr = self.attr_combo.currentText().strip()
        if not attr:
            QMessageBox.warning(self, "Assign to Instance",
                                "Enter an attribute name.")
            return

        item = self.instance_table.find_instance_item(instance_name)
        if item is None:
            QMessageBox.warning(self, "Assign to Instance",
                                f"Instance '{instance_name}' was not found.")
            return

        value, per_corner, reduce_label = self._resolve()
        axis = self.source_combo.currentData()
        axis_label = self.axis_names[axis]
        pinned_axis = self._pinned_axis()
        pinned_value = self.readouts[0][pinned_axis]

        if attr not in self.instance_table.columns and self.add_column_check.isChecked():
            self.instance_table.add_column(attr)

        spec = {
            "mode": "pinned",
            "resolved": value,
            "reduce": reduce_label,
            "per_corner": per_corner,
            "as_column": attr in self.instance_table.columns,
            "source_label": (f"{axis_label} at "
                             f"{self.axis_names[pinned_axis]}="
                             f"{format_param_value(pinned_value)}"),
        }
        self.instance_table.set_instance_attribute(item, attr, spec)
        self.accept()
