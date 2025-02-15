import sys
import json
import gdstk
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QTextEdit, QGraphicsView, QGraphicsScene, QGraphicsRectItem
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt
sys.path.append("/home/adair/Documents/CAD/align/ALIGN-public")
import align


class DraggableRect(QGraphicsRectItem):
    def __init__(self, x, y, w, h, name):
        super().__init__(x, y, w, h)
        self.setBrush(QColor("lightblue"))
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.name = name

class AlignConstraintsGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.netlist_file = "example.sp"
        self.constraints = {}
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Netlist Selection
        self.netlist_label = QLabel(f"Netlist File: {self.netlist_file}")
        
        # Constraints Input
        self.constraints_label = QLabel("Constraints JSON:")
        self.constraints_editor = QTextEdit()
        self.constraints_editor.setPlaceholderText("Enter constraints JSON here...")
        
        # Generate Constraints File
        self.generate_constraints_btn = QPushButton("Generate Constraints")
        self.generate_constraints_btn.clicked.connect(self.generate_constraints)
        
        # Run ALIGN
        self.run_align_btn = QPushButton("Run ALIGN")
        self.run_align_btn.clicked.connect(self.run_align)
        
        # Layout Preview
        self.layout_view = QGraphicsView()
        self.layout_scene = QGraphicsScene()
        self.layout_view.setScene(self.layout_scene)
        
        # Load GDS Preview Button
        self.load_gds_btn = QPushButton("Load GDS Preview")
        self.load_gds_btn.clicked.connect(self.load_gds)
        
        # Output Log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        # Add widgets to layout
        layout.addWidget(self.netlist_label)
        layout.addWidget(self.constraints_label)
        layout.addWidget(self.constraints_editor)
        layout.addWidget(self.generate_constraints_btn)
        layout.addWidget(self.run_align_btn)
        layout.addWidget(self.layout_view)
        layout.addWidget(self.load_gds_btn)
        layout.addWidget(self.log_output)
        
        self.setLayout(layout)
        self.setWindowTitle("ALIGN Constraints Editor")
        self.setGeometry(100, 100, 800, 600)
        self.load_example_circuit()
    
    def load_example_circuit(self):
        example_constraints = {
            "placement": [
                {"name": "M1", "x": 0, "y": 0},
                {"name": "M2", "x": 50, "y": 0},
                {"name": "M3", "x": 0, "y": 50},
                {"name": "M4", "x": 50, "y": 50}
            ]
        }
        self.constraints_editor.setText(json.dumps(example_constraints, indent=4))
        self.generate_preview()
    
    def generate_constraints(self):
        try:
            constraints_text = self.constraints_editor.toPlainText()
            self.constraints = json.loads(constraints_text)
            constraints_file = "example_constraints.json"
            
            with open(constraints_file, "w") as f:
                json.dump(self.constraints, f, indent=4)
            
            self.generate_preview()
        except json.JSONDecodeError:
            self.constraints_editor.setText("Invalid JSON format. Please check your constraints.")
    
    def generate_preview(self):
        self.layout_scene.clear()
        
        if "placement" in self.constraints:
            for cell in self.constraints["placement"]:
                x, y = cell["x"], cell["y"]
                rect = DraggableRect(x, y, 40, 40, cell["name"])
                self.layout_scene.addItem(rect)
    
    def run_align(self):
        self.log_output.append("Running ALIGN...")
        command = ["python", "-m", "align.pnr.main", self.netlist_file, "--pdk", "pdks/sky130A"]
        try:
            process = subprocess.run(command, capture_output=True, text=True, check=True)
            self.log_output.append(process.stdout)
            self.load_gds("./results/gds/example.gds")  # Auto-load the generated GDS
        except subprocess.CalledProcessError as e:
            self.log_output.append(f"ALIGN error: {e.stderr}")
    
    def load_gds(self, gds_file=None):
        if not gds_file:
            gds_file, _ = QFileDialog.getOpenFileName(self, "Select GDS File", "", "GDS Files (*.gds)")
        
        if gds_file:
            self.display_gds(gds_file)
    
    def display_gds(self, gds_file):
        self.layout_scene.clear()
        
        gds_lib = gdstk.read_gds(gds_file)
        for cell in gds_lib.cells:
            for polygon in cell.polygons:
                points = polygon.points
                if len(points) > 1:
                    path = self.layout_scene.addPolygon(QColor("green"))
                    path.setPolygon(points)
        self.log_output.append(f"Loaded GDS: {gds_file}")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlignConstraintsGUI()
    window.show()
    sys.exit(app.exec())
