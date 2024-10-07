import tkinter as tk
from tkinter import ttk

class SidePanelApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Side Panel with Tabs")
        self.geometry("800x600")

        # Create a main horizontal pane with side panel and content area
        self.main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the side panel (left)
        self.side_panel_frame = ttk.Frame(self.main_pane, width=200)
        self.main_pane.add(self.side_panel_frame, weight=0)

        # Create a frame for the main content area (right)
        self.content_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.content_frame, weight=1)

        # Add side panel with tabs (notebook)
        self.create_side_panel()

    def create_side_panel(self):
        """Creates the side panel with vertical tabs."""
        notebook = ttk.Notebook(self.side_panel_frame)

        # Create tabs for different sections
        lut_tab = ttk.Frame(notebook)
        device_xplore_tab = ttk.Frame(notebook)
        ddb_generation_tab = ttk.Frame(notebook)
        design_xplore_tab = ttk.Frame(notebook)
        code_dive_tab = ttk.Frame(notebook)

        # Add tabs to notebook with labels
        notebook.add(lut_tab, text="LUT Generation")
        notebook.add(device_xplore_tab, text="Device Xplore")
        notebook.add(ddb_generation_tab, text="DDB Generation")
        notebook.add(design_xplore_tab, text="Design Xplore")
        notebook.add(code_dive_tab, text="Code Dive")

        # Pack the notebook to fill the side panel
        notebook.pack(expand=True, fill=tk.BOTH)

        # Example content for LUT Generation tab
        ttk.Label(lut_tab, text="LUT Generation Content").pack(padx=10, pady=10)
        ttk.Label(device_xplore_tab, text="Device Xplore Content").pack(padx=10, pady=10)
        ttk.Label(ddb_generation_tab, text="DDB Generation Content").pack(padx=10, pady=10)
        ttk.Label(design_xplore_tab, text="Design Xplore Content").pack(padx=10, pady=10)
        ttk.Label(code_dive_tab, text="Code Dive Content").pack(padx=10, pady=10)

# Initialize the app
if __name__ == "__main__":
    app = SidePanelApp()
    app.mainloop()
