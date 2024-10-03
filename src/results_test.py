import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json

class CIDColumnResults(ttk.LabelFrame):
    def __init__(self, master, top_level_app):
        super().__init__(master, text="Expression Results")
        self.top_level_app = top_level_app
        self.top_frame = ttk.Frame(self)
        self.canvas = tk.Canvas(self.top_frame)
        self.internal_frame = ttk.Frame(self.canvas)
        self.v_scrollbar = ttk.Scrollbar(self.top_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self.top_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.top_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.internal_frame, anchor="nw")
        self.bind_mouse_scroll()
        self.paned_window = ttk.PanedWindow(self.internal_frame, orient=tk.HORIZONTAL)

        self.symbol_frame = ttk.Frame(self.paned_window)
        self.function_frame = ttk.Frame(self.paned_window)

        self.paned_window.add(self.symbol_frame, weight=1)  # Symbol frame stretches
        self.paned_window.add(self.function_frame, weight=3)  # Function frame stretches more

        self.paned_window.pack(fill=tk.BOTH, expand=True)
        self.symbol_frame.grid_columnconfigure(0, weight=1)
        self.function_frame.grid_columnconfigure(0, weight=1)

        self.current_row = 1  # Start at 1 because row 0 is for titles
        self.num_entries = 0
        self.entries = []
        self.bind("<Configure>", self.resize_internal_frame)

        self.create_titles()
        self.add_row()

    def create_titles(self):
        """Create the title row for the grid in each column."""
        ttk.Label(self.symbol_frame, text="").grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        ttk.Label(self.function_frame, text="").grid(row=0, column=0, padx=1, pady=1, sticky="ew")

    def add_row(self):
        """Add a new row to the grid for symbol, function, and options."""
        symbol_entry = ttk.Entry(self.symbol_frame, width=6)
        function_entry = ttk.Entry(self.function_frame, width=6)

        symbol_entry.grid(row=self.current_row, column=0, padx=1, pady=3.5, sticky="ew")
        function_entry.grid(row=self.current_row, column=0, padx=1, pady=3.5, sticky="ew")

        self.entries.append((symbol_entry, function_entry))

        self.current_row += 1
        self.num_entries += 1
        self.update_scroll_region()

    def update_scroll_region(self, event=None):
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def resize_internal_frame(self, event):
        canvas_width = event.width - 10
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def bind_mouse_scroll(self):
        """Bind mouse wheel scrolling to the canvas."""
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # For Windows and Mac
        self.canvas.bind("<Button-4>", self._on_mousewheel)    # For Linux scrolling up
        self.canvas.bind("<Button-5>", self._on_mousewheel)     # For Linux scrolling down

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")  # Scroll up
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")   # Scroll down


# Application setup
class ExampleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CIDColumnResults Window Example")
        self.geometry("600x400")

        # Simulate the top_level_app object used in CIDColumnResults
        self.lookups = ["Var1", "Var2", "Var3"]

        # Create and pack the CIDColumnResults inside the window
        self.column_results = CIDColumnResults(self, self)
        self.column_results.pack(fill=tk.BOTH, expand=True)


# Run the application
if __name__ == "__main__":
    app = ExampleApp()
    app.mainloop()
