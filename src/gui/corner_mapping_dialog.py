"""
Corner Mapping Dialog for 3D Plotting

This dialog helps users set up valid corner configurations for 3D plotting
by visualizing which corners each device uses and ensuring compatibility.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush


class CornerMappingDialog(QDialog):
    """Dialog for visualizing and configuring corner mappings for 3D plotting."""
    
    corner_mapping_changed = pyqtSignal()
    
    def __init__(self, parent, design_editor, tech_browser):
        super().__init__(parent)
        self.design_editor = design_editor
        self.tech_browser = tech_browser
        self.setWindowTitle("3D Plot Corner Mapping")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        self.update_corner_info()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with explanation
        header = QLabel(
            "<b>Corner Mapping for 3D Plotting</b><br>"
            "For 3D plotting to work correctly, all devices used in equations must have "
            "the <b>same number of corners</b>. This dialog shows the current corner "
            "configuration and helps you fix any mismatches."
        )
        header.setWordWrap(True)
        header.setStyleSheet("padding: 10px; background-color: #e8f4f8; border-radius: 5px;")
        layout.addWidget(header)
        
        # Corner mapping table
        table_group = QGroupBox("Device Corner Configuration")
        table_layout = QVBoxLayout()
        
        self.corner_table = QTableWidget()
        self.corner_table.setColumnCount(5)
        self.corner_table.setHorizontalHeaderLabels([
            "Device", "Selection Type", "# Corners", "Corner Names", "Status"
        ])
        
        # Make table read-only
        self.corner_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set column widths
        header = self.corner_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.corner_table.setColumnWidth(0, 80)
        self.corner_table.setColumnWidth(2, 80)
        
        table_layout.addWidget(self.corner_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Status summary
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 8px; border-radius: 3px;")
        layout.addWidget(self.status_label)
        
        # Quick fix section
        fix_group = QGroupBox("Quick Fix Options")
        fix_layout = QVBoxLayout()
        
        fix_info = QLabel(
            "If corner counts don't match, use one of these options to fix:"
        )
        fix_layout.addWidget(fix_info)
        
        # Option 1: Set all to global
        global_btn_layout = QHBoxLayout()
        self.set_all_global_btn = QPushButton("Set All Devices to Global")
        self.set_all_global_btn.setToolTip(
            "Sets all devices to use global (tech browser) selection.\n"
            "All devices will then use the same corners."
        )
        self.set_all_global_btn.clicked.connect(self.set_all_to_global)
        global_btn_layout.addWidget(self.set_all_global_btn)
        global_btn_layout.addStretch()
        fix_layout.addLayout(global_btn_layout)
        
        # Option 2: Pad to match maximum
        pad_btn_layout = QHBoxLayout()
        self.pad_corners_btn = QPushButton("Match All to Maximum Corner Count")
        self.pad_corners_btn.setToolTip(
            "Finds the device with the most corners and prompts you to\n"
            "select the same number of corners for all other devices."
        )
        self.pad_corners_btn.clicked.connect(self.match_to_maximum)
        self.pad_corners_btn.setEnabled(False)  # Enable only if there's a mismatch
        pad_btn_layout.addWidget(self.pad_corners_btn)
        pad_btn_layout.addStretch()
        fix_layout.addLayout(pad_btn_layout)
        
        fix_group.setLayout(fix_layout)
        layout.addWidget(fix_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.update_corner_info)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def update_corner_info(self):
        """Update the table with current corner configuration."""
        if not self.design_editor:
            return
            
        device_corners = self.design_editor.get_device_corners()
        
        self.corner_table.setRowCount(len(device_corners))
        
        corner_counts = {}
        all_corner_counts = []
        
        row = 0
        for device_name, device_info in device_corners.items():
            # Device name
            name_item = QTableWidgetItem(device_name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.corner_table.setItem(row, 0, name_item)
            
            # Selection type and corner info
            corners = device_info.get('corners')
            corner_paths = device_info.get('corner_paths')
            
            if corners is None:
                # Global selection
                selection_type = "Global"
                # Count corners from tech browser (current selection)
                corner_count = self.count_tech_browser_corners()
                corner_names = "[Uses tech browser selection]"
                status = "✓ Global"
                status_color = QColor("#90EE90")  # Light green
            else:
                # Device-specific
                selection_type = "Device-Specific"
                corner_count = len(corners)
                corner_names = ", ".join(corners) if corners else "None"
                status = "✓ Custom"
                status_color = QColor("#87CEEB")  # Sky blue
                
            all_corner_counts.append(corner_count)
            corner_counts[device_name] = corner_count
            
            # Selection type
            type_item = QTableWidgetItem(selection_type)
            self.corner_table.setItem(row, 1, type_item)
            
            # Corner count
            count_item = QTableWidgetItem(str(corner_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Highlight if count doesn't match majority
            if all_corner_counts and corner_count != max(set(all_corner_counts), key=all_corner_counts.count):
                count_item.setBackground(QBrush(QColor("#FFE4B5")))  # Moccasin (warning)
                
            self.corner_table.setItem(row, 2, count_item)
            
            # Corner names
            names_item = QTableWidgetItem(corner_names)
            self.corner_table.setItem(row, 3, names_item)
            
            # Status
            status_item = QTableWidgetItem(status)
            status_item.setBackground(QBrush(status_color))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.corner_table.setItem(row, 4, status_item)
            
            row += 1
            
        # Update status summary
        self.update_status_summary(corner_counts)
        
    def count_tech_browser_corners(self):
        """Count how many corners are currently selected in tech browser."""
        if not self.tech_browser:
            return 0
            
        try:
            if hasattr(self.tech_browser, 'get_checked_item_paths'):
                paths = self.tech_browser.get_checked_item_paths()
                # Count unique corner names (last part of path)
                corner_names = set()
                for path in paths:
                    parts = path.split('>')
                    if len(parts) >= 5:
                        corner_names.add(parts[4])
                return len(corner_names)
        except Exception:
            pass
            
        return 0
        
    def update_status_summary(self, corner_counts):
        """Update the status summary based on corner counts."""
        if not corner_counts:
            self.status_label.setText("No devices found in instance table.")
            self.status_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 3px;")
            return
            
        unique_counts = set(corner_counts.values())
        
        if len(unique_counts) == 1:
            # All devices have same corner count - GOOD!
            count = list(unique_counts)[0]
            self.status_label.setText(
                f"✓ <b>Configuration is VALID for 3D plotting!</b><br>"
                f"All {len(corner_counts)} devices use {count} corner(s)."
            )
            self.status_label.setStyleSheet("padding: 8px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")
            self.pad_corners_btn.setEnabled(False)
        else:
            # Mismatched corner counts - PROBLEM!
            count_summary = ", ".join(f"{device}: {count}" for device, count in corner_counts.items())
            self.status_label.setText(
                f"⚠ <b>Configuration has MISMATCHED corner counts!</b><br>"
                f"3D plotting may not work correctly with mixed corner counts.<br>"
                f"Corner counts by device: {count_summary}<br>"
                f"<i>Use the Quick Fix options below to resolve this.</i>"
            )
            self.status_label.setStyleSheet("padding: 8px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 3px; color: #856404;")
            self.pad_corners_btn.setEnabled(True)
            
    def set_all_to_global(self):
        """Set all devices to use global corner selection."""
        if not self.design_editor:
            return
            
        reply = QMessageBox.question(
            self,
            "Set All to Global?",
            "This will set ALL devices in the instance table to use global (tech browser) selection.\n\n"
            "All device-specific corner selections will be cleared.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Set all devices to global (None)
        instance_table = self.design_editor.instance_table
        corners_col = instance_table.corners_column_index
        
        if corners_col >= 0:
            for i in range(instance_table.tree.topLevelItemCount()):
                item = instance_table.tree.topLevelItem(i)
                instance_table.update_corners_display(item, None)
                
        self.update_corner_info()
        self.corner_mapping_changed.emit()
        
        QMessageBox.information(
            self,
            "Success",
            "All devices have been set to use global corner selection.\n\n"
            "They will now all use the corners selected in the main tech browser."
        )
        
    def match_to_maximum(self):
        """Show guidance for matching all devices to maximum corner count."""
        if not self.design_editor:
            return
            
        device_corners = self.design_editor.get_device_corners()
        
        # Find maximum corner count
        max_count = 0
        max_device = None
        for device, info in device_corners.items():
            corners = info.get('corners')
            count = len(corners) if corners else self.count_tech_browser_corners()
            if count > max_count:
                max_count = count
                max_device = device
                
        QMessageBox.information(
            self,
            "Match Corner Counts",
            f"The maximum corner count is {max_count} (from device {max_device}).\n\n"
            f"To match all devices to this count:\n\n"
            f"1. For each device, click the 'Corners' cell in the instance table\n"
            f"2. In the tech browser popup, select exactly {max_count} corners\n"
            f"3. Click 'Apply'\n"
            f"4. Repeat for all devices\n\n"
            f"Alternative: Use 'Set All Devices to Global' and select {max_count} corners "
            f"in the main tech browser."
        )
        
    def get_device_corners_dict(self):
        """Get the current device corners configuration."""
        if self.design_editor:
            return self.design_editor.get_device_corners()
        return {}
