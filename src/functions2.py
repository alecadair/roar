import tkinter as tk
import os
from tkinter import ttk

ROAR_HOME = os.environ["ROAR_HOME"]
ROAR_LIB = os.environ["ROAR_LIB"]
ROAR_SRC = os.environ["ROAR_SRC"]
ROAR_CHARACTERIZATION = os.environ["ROAR_CHARACTERIZATION"]
ROAR_DESIGN_SCRIPTS = os.environ["ROAR_DESIGN_SCRIPTS"]
ROAR_IMAGES = ROAR_HOME + "/images"
ROAR_SVG = ROAR_IMAGES + "/svg/"
ROAR_PNG = ROAR_IMAGES + "/png/"

class EquationBuilder(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Equation Builder")
        self.geometry("800x400")
        self.buttons_frame = ttk.Frame(self)
        self.add_row_button = ttk.Button(self.buttons_frame, text="Add Row", command=self.add_row)
        self.add_row_button.pack(pady=5, side=tk.LEFT)
        self.save_state_button = ttk.Button(self.buttons_frame, text="Save", command=self.save_state)
        self.load_state_button = ttk.Button(self.buttons_frame, text="Load", command=self.load_state)
        self.load_state_button.pack(pady=5,side=tk.RIGHT)
        self.save_state_button.pack(pady=5,side=tk.RIGHT)
        self.buttons_frame.pack(pady=5, side=tk.BOTTOM)
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
        #self.internal_frame.bind("<Configure>", self.update_scroll_region)

        #self.internal_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        #self.internal_frame.grid_rowconfigure(0, weight=1)
        self.bind("<Configure>", self.resize_internal_frame)
        # Create a PanedWindow for the entire app with horizontal layout
        self.paned_window = ttk.PanedWindow(self.internal_frame, orient=tk.HORIZONTAL)
        #self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Create separate frames for each column in the PanedWindow
        self.symbol_frame = ttk.Frame(self.paned_window)
        self.function_frame = ttk.Frame(self.paned_window)
        self.options_frame = ttk.Frame(self.paned_window)

        # Add frames to the PanedWindow
        self.paned_window.add(self.symbol_frame, weight=1)      # Symbol frame stretches
        self.paned_window.add(self.function_frame, weight=3)    # Function frame stretches more
        self.paned_window.add(self.options_frame, weight=0)     # Options frame does not stretch
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        # Configure column resizing in function_frame
        self.symbol_frame.grid_columnconfigure(0, weight=1)
        self.function_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(0, weight=1)

        self.delete_icon_path = ROAR_PNG + "delete_icon.png"
        self.delete_icon_image = tk.PhotoImage(file=self.delete_icon_path)



        # Keep track of grid rows
        self.current_row = 1 # Start at 1 because row 0 is for titles
        self.num_entries = 0
        self.entries = []

        # Add a button to add new rows (place outside the PanedWindow)
  # Ensure the button is placed below the paned window
        #self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        #self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        #self.top_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        #self.canvas.pack(fill=tk.BOTH, expand=True)

        #self.canvas.pack(fill=tk.BOTH, expand=True)
        #self.internal_frame.pack(fill=tk.X, expand=False)
        #self.internal_frame.grid()
        #self.paned_window.pack(fill=tk.BOTH, expand=True)
        #self.bind("<Configure>", self.on_resize)

        # Add column titles
        self.create_titles()
        # Add initial row
        self.add_row()
        #self.bind("<Configure>", self.on_resize)


    def create_titles(self):
        """Create the title row for the grid in each column."""
        ttk.Label(self.symbol_frame, text="Symbol").grid(row=0, column=0, padx=1, pady=1, sticky="ew" )
        ttk.Label(self.function_frame, text="Function").grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        ttk.Label(self.options_frame, text="Options").grid(row=0, column=0, padx=5, pady=1, sticky="ew")

    def add_row(self):
        """Add a new row to the grid for symbol, function, and options."""

        # Create entries for symbol, function, and options in their respective panes
        symbol_entry = ttk.Entry(self.symbol_frame, width=15)
        function_entry = ttk.Entry(self.function_frame)
        options_combobox = ttk.Combobox(self.options_frame, values=["Maximize", "Minimize", "Constraint"], width=10)
        options_combobox.current(0)  # Set default to "Maximize"

        # Initialize the checkbox with a default checked state
        enable_row = tk.IntVar(value=1)
        enable_checkbox = tk.Checkbutton(self.options_frame, variable=enable_row,
                                         command=lambda: self.toggle_edit(enable_row, symbol_entry, function_entry))

        # Button to delete the row
        delete_button = tk.Button(self.options_frame, image=self.delete_icon_image,
                                  command=lambda: self.delete_row(symbol_entry, function_entry, options_combobox, enable_checkbox, delete_button))

        # Adjust button size to fit the image
        delete_button.config(width=self.delete_icon_image.width(), height=self.delete_icon_image.height())
        delete_button.config(bd=0, highlightthickness=0, relief="flat")

        # Place the widgets in the grid within their respective columns
        symbol_entry.grid(row=self.current_row, column=0, padx=1, pady=1, sticky="ew")
        function_entry.grid(row=self.current_row, column=0, padx=1, pady=1, sticky="ew")  # Sticky for full width
        options_combobox.grid(row=self.current_row, column=0, padx=1, pady=1, sticky="ew")
        enable_checkbox.grid(row=self.current_row, column=1, padx=1, pady=1, sticky="ew")
        delete_button.grid(row=self.current_row, column=2, padx=1, pady=1, sticky="ew")

        # Store the row entries for later access or deletion (including the checkbox)
        self.entries.append((symbol_entry, function_entry, options_combobox, enable_checkbox, delete_button))
        #self.internal_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))


        # Increment row counter
        self.current_row += 1
        self.num_entries += 1
        self.update_scroll_region()


    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def toggle_edit(self, enable_row, symbol_entry, function_entry):
        """Enable or disable editing of the entries based on the checkbox state."""
        if enable_row.get() == 1:
            # Enable editing when checkbox is checked (default)
            symbol_entry.config(state="normal")
            function_entry.config(state="normal")
        else:
            # Disable editing when checkbox is unchecked
            symbol_entry.config(state="disabled")
            function_entry.config(state="disabled")

    def delete_row(self, symbol_entry, function_entry, options_combobox, enable_checkbox, delete_button):
        """Delete the specific row."""
        # Remove widgets from the grid
        if self.num_entries == 0:
            return 0
        symbol_entry.grid_forget()
        function_entry.grid_forget()
        options_combobox.grid_forget()
        enable_checkbox.grid_forget()  # Remove the checkbox
        delete_button.grid_forget()

        # Remove the row from the list
        self.entries = [(s, f, o, e, d) for s, f, o, e, d in self.entries if s != symbol_entry]
        self.num_entries -= 1
        self.update_scroll_region()

    def on_resize(self, event):
        right_pane_width = self.winfo_width() - self.paned_window.sashpos(1)
        if right_pane_width > self.options_width:
            new_sash_position = self.winfo_width() - self.options_width
            self.paned_window.sashpos(1, new_sash_position)
        self.internal_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def resize_internal_frame(self, event):
        canvas_width = self.canvas.winfo_width()
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def save_state(self):
        """Save the current state of the EquationBuilder to a user-selected JSON file."""
        # Open file dialog to ask user where to save the file
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])

        if not file_path:
            return  # User canceled the dialog

        state_data = []
        for entry in self.entries:
            symbol_entry, function_entry, options_combobox, enable_checkbox, _ = entry
            symbol = symbol_entry.get()
            function = function_entry.get()
            option = options_combobox.get()
            enable = enable_checkbox.var.get()

            state_data.append({
                "symbol": symbol,
                "function": function,
                "option": option,
                "enable": enable
            })

        # Save the data to the selected file
        with open(file_path, "w") as f:
            json.dump(state_data, f)


    def load_state(self):
        """Load the state from a user-selected JSON file and populate the EquationBuilder."""
        # Open file dialog to ask user which file to load
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])

        if not file_path:
            return  # User canceled the dialog

        try:
            with open(file_path, "r") as f:
                state_data = json.load(f)

            # Clear current entries
            for entry in self.entries:
                symbol_entry, function_entry, options_combobox, enable_checkbox, delete_button = entry
                self.delete_row(symbol_entry, function_entry, options_combobox, enable_checkbox, delete_button)

            # Add rows from loaded state
            for row in state_data:
                self.add_row(row["symbol"], row["function"], row["option"], row["enable"])

        except FileNotFoundError:
            print("No saved state found.")

# Initialize the main application window
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x600")

    # Create a button to open the Equation Builder
    def open_equation_builder():
        builder = EquationBuilder(master=root)
        #builder.grab_set()

    open_button = ttk.Button(root, text="Open Equation Builder", command=open_equation_builder)
    open_button.pack(pady=20)

    root.mainloop()
