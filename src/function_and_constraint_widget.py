import tkinter as tk
from tkinter import ttk

class EquationBuilder(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Equation Builder")
        self.geometry("800x400")

        # Create a PanedWindow for the entire app with horizontal layout
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Create separate frames for each column in the PanedWindow
        self.symbol_frame = ttk.Frame(self.paned_window)
        self.function_frame = ttk.Frame(self.paned_window)
        self.options_frame = ttk.Frame(self.paned_window)

        # Add frames to the PanedWindow
        self.paned_window.add(self.symbol_frame, weight=1)      # Symbol frame stretches
        self.paned_window.add(self.function_frame, weight=3)    # Function frame stretches more
        self.paned_window.add(self.options_frame, weight=0)     # Options frame does not stretch

        # Configure column resizing in function_frame
        self.function_frame.grid_columnconfigure(0, weight=1)  # Ensure the function entry stretches

        # Add column titles
        self.create_titles()

        # Keep track of grid rows
        self.current_row = 1  # Start at 1 because row 0 is for titles
        self.entries = []

        # Add initial row
        self.add_row()

        # Add a button to add new rows
        self.add_row_button = ttk.Button(self, text="Add Row", command=self.add_row)
        self.add_row_button.pack(pady=10)

    def create_titles(self):
        """Create the title row for the grid in each column."""
        ttk.Label(self.symbol_frame, text="Symbol").grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(self.function_frame, text="Function").grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(self.options_frame, text="Options").grid(row=0, column=0, padx=10, pady=5)

    def add_row(self):
        """Add a new row to the grid for symbol, function, and options."""

        # Create entries for symbol, function, and options in their respective panes
        symbol_entry = ttk.Entry(self.symbol_frame, width=15)
        function_entry = ttk.Entry(self.function_frame)
        options_combobox = ttk.Combobox(self.options_frame, values=["Maximize", "Minimize", "Constraint"], width=15)
        options_combobox.current(0)  # Set default to "Maximize"

        # Button to delete the row
        delete_button = ttk.Button(self.options_frame, text="Delete", command=lambda: self.delete_row(symbol_entry, function_entry, options_combobox, delete_button))

        # Place the widgets in the grid within their respective columns
        symbol_entry.grid(row=self.current_row, column=0, padx=5, pady=5, sticky="nsew")
        function_entry.grid(row=self.current_row, column=0, padx=5, pady=5, sticky="nsew")  # Sticky for full width
        options_combobox.grid(row=self.current_row, column=0, padx=5, pady=5, sticky="nsew")
        delete_button.grid(row=self.current_row, column=1, padx=5, pady=5, sticky="nsew")

        # Store the row entries for later access or deletion
        self.entries.append((symbol_entry, function_entry, options_combobox, delete_button))

        # Increment row counter
        self.current_row += 1

    def delete_row(self, symbol_entry, function_entry, options_combobox, delete_button):
        """Delete the specific row."""
        # Remove widgets from the grid
        symbol_entry.grid_forget()
        function_entry.grid_forget()
        options_combobox.grid_forget()
        delete_button.grid_forget()

        # Remove the row from the list
        self.entries = [(s, f, o, d) for s, f, o, d in self.entries if s != symbol_entry]


# Initialize the main application window
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x600")

    # Create a button to open the Equation Builder
    def open_equation_builder():
        builder = EquationBuilder(master=root)
        builder.grab_set()

    open_button = ttk.Button(root, text="Open Equation Builder", command=open_equation_builder)
    open_button.pack(pady=20)

    root.mainloop()
