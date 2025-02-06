from PyQt5.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QScrollBar, QFileDialog, QInputDialog
)

class CIDTechBrowser(QWidget):
    def __init__(self, parent, lookup_window, top_level_app):
        super().__init__(parent)
        self.parent = parent
        self.top_level_app = top_level_app
        self.lookup_window = lookup_window
        self.graphing_widget = None

        # Layout for the widget
        layout = QVBoxLayout(self)

        # Scrollbar
        self.scrollbar = QScrollBar()
        
        # Tree widget with checkboxes
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.select_item)
        
        layout.addWidget(self.tree)
        layout.addWidget(self.scrollbar)

        self.tree_item_counter = 0
        self.tech_dict = top_level_app.tech_dict

        # Add root item "PDK"
        self.pdk_item = QTreeWidgetItem(self.tree, ["PDK"])
        self.tree.addTopLevelItem(self.pdk_item)

    def get_selected_corners(self):
        """Return the paths of all checked root nodes (omitting sublevels)."""
        selected_corners = set()
        root = self.tree.invisibleRootItem()
        
        def traverse_tree(item, path):
            """Recursively traverse the tree to find selected checkboxes."""
            if item.checkState(0) == 2:  # 2 is checked state
                selected_corners.add(">".join(path))

            for i in range(item.childCount()):
                traverse_tree(item.child(i), path + [item.child(i).text(0)])

        traverse_tree(root, [])
        return list(selected_corners)

    def select_item(self, item, column):
        """Handle item selection and update graph."""
        if self.lookup_window is not None:
            self.lookup_window.update_graph_from_tech_browser()

    def set_graphing_widget(self, graphing_widget):
        self.graphing_widget = graphing_widget

    def add_tech_luts(self, dirname=None, pdk_name=None):
        if dirname is None:
            lut_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
            pdk, ok = QInputDialog.getText(self, "Technology Process Name", "Enter process name (e.g., sky130)")
            if not ok:
                return
        else:
            lut_dir, pdk = dirname, pdk_name

        pdk_item = QTreeWidgetItem(self.pdk_item, [pdk])
        self.pdk_item.addChild(pdk_item)

        pdk_dict = self.top_level_app.tech_dict.get(pdk, {})

        delim = ">"
        for model in pdk_dict:
            model_item = QTreeWidgetItem(pdk_item, [model])
            pdk_item.addChild(model_item)

            model_dict = pdk_dict[model]
            for length in model_dict:
                length_item = QTreeWidgetItem(model_item, [length])
                model_item.addChild(length_item)

                device = model_dict[length]["device"]
                for corner in device.corners:
                    corner_item = QTreeWidgetItem(length_item, [corner.corner_name])
                    length_item.addChild(corner_item)

    def add_tech_from_dir(self, dir, pdk_name):
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            model_dir = os.path.join(dir, filename)
            if os.path.isdir(model_dir):
                self.create_devices_from_model_dir(pdk_name, filename, model_dir)
        self.add_tech_luts(dirname=dir, pdk_name=pdk_name)

    def create_devices_from_model_dir(self, pdk_name, model_name, model_dir):
        self.tech_dict[pdk_name][model_name] = {}
        for filename in os.listdir(model_dir):
            length_dir = os.path.join(model_dir, filename)
            tokens = filename.split('_')
            length = tokens[-1]
            device = CIDDevice(device_name=model_name, vdd=0.0, lut_directory=length_dir, corner_list=None)
            self.tech_dict[pdk_name][model_name][length] = {"device": device, "corners": {}}
            
            for corner in device.corners:
                self.tech_dict[pdk_name][model_name][length]["corners"][corner.corner_name] = corner
        return(self.tech_dict)
