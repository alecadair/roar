import tkinter as tk
from tkinter import ttk, filedialog
import json

class BaseEditor(ttk.LabelFrame):
    def __init__(self, parent, title, columns, left_justify_columns=None, column_ratios=None, plot_button_text="Add LUT"):
        super().__init__(parent, text=title)
        self.columns = columns
        self.left_justify_columns = left_justify_columns if left_justify_columns else []
        self.column_ratios = column_ratios if column_ratios else [1] * len(columns)  # Default ratio of 1:1 for columns
        self.plot_button_text = plot_button_text
        self.disabled_rows = set()
        self.enabled_plot_rows = set()
        self.setup_widgets()

    def setup_widgets(self):
        """Set up the Treeview, buttons, and layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create the Treeview with alternating row colors
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        total_weight = sum(self.column_ratios)

        for i, col in enumerate(self.columns):
            justify = "w" if col in self.left_justify_columns else "center"  # Left justify if needed
            width = int(self.winfo_width() * (self.column_ratios[i] / total_weight))  # Calculate width based on ratios
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=justify, width=width)

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Vertical scrollbar
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.vsb.grid(row=0, column=1, sticky="ns")

        # Add an empty row initially
        self.add_row()

        # Create frames for the buttons
        button_frame_1 = ttk.Frame(self)
        button_frame_1.grid(row=1, column=0, sticky="ew", pady=5)

        # Row 1: Add Row, Delete Row, Enable/Disable, Add LUT/Set LUTs
        self.add_button = ttk.Button(button_frame_1, text="+", command=self.add_row)
        self.add_button.pack(side="left", padx=5, fill="x", expand=True)

        self.delete_button = ttk.Button(button_frame_1, text="-", command=self.delete_row)
        self.delete_button.pack(side="left", padx=5, fill="x", expand=True)

        self.enable_disable_button = ttk.Button(button_frame_1, text="Enable/Disable", command=self.toggle_enable_disable_row)
        self.enable_disable_button.pack(side="left", padx=5, fill="x", expand=True)

        self.plot_button = ttk.Button(button_frame_1, text=self.plot_button_text, command=self.toggle_plot_highlight)
        self.plot_button.pack(side="left", padx=5, fill="x", expand=True)

        # Enable editing functionality
        self.tree.bind("<Double-1>", self.on_double_click)

    def add_row(self):
        """Add an empty row to the treeview and apply alternating row colors."""
        children = self.tree.get_children()
        new_tag = "oddrow" if len(children) % 2 == 0 else "evenrow"
        self.tree.insert("", "end", values=tuple([""] * len(self.columns)), tags=(new_tag,))
        self.apply_row_color_scheme()

    def delete_row(self):
        """Delete the selected row from the treeview and reapply alternating row colors."""
        selected_item = self.tree.selection()
        if selected_item:
            self.tree.delete(selected_item)
            self.reapply_alternating_colors()

    def reapply_alternating_colors(self):
        """Reapply alternating row colors to the table while keeping the disabled and plotted rows intact."""
        self.apply_row_color_scheme()

    def apply_row_color_scheme(self):
        """Apply alternating row colors while preserving disabled and plotted row colors."""
        for i, row in enumerate(self.tree.get_children()):
            if row in self.disabled_rows:
                self.tree.item(row, tags=("disabled",))
                self.tree.tag_configure("disabled", background="#FFB6C1")  # Disabled rows (lighter red)
            elif row in self.enabled_plot_rows:
                self.tree.item(row, tags=("plot",))
                self.tree.tag_configure("plot", background="#90EE90")  # Plotted rows (lighter green)
            else:
                # Apply alternating row colors for regular rows
                new_tag = "oddrow" if i % 2 == 0 else "evenrow"
                self.tree.item(row, tags=(new_tag,))
                self.tree.tag_configure("oddrow", background="white")
                self.tree.tag_configure("evenrow", background="lightgray")

    def on_double_click(self, event):
        """Handle double-click event to enable cell editing."""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            row_id = self.tree.identify_row(event.y)

            # Create entry widget for editing
            col_index = int(column[1:]) - 1
            item = self.tree.item(row_id)
            value = item["values"][col_index]

            # Create an entry widget over the cell
            x, y, width, height = self.tree.bbox(row_id, column)
            entry = tk.Entry(self, width=width // 10)
            entry.place(x=x + self.tree.winfo_x(), y=y + self.tree.winfo_y(), width=width, height=height)
            entry.insert(0, value)
            entry.focus()

            # Save the new value on Return key
            def save_value(event):
                new_value = entry.get()
                values = list(item["values"])
                values[col_index] = new_value
                self.tree.item(row_id, values=values)
                entry.destroy()

            entry.bind("<Return>", save_value)
            entry.bind("<FocusOut>", lambda e: entry.destroy())

    def toggle_enable_disable_row(self):
        """Enable or disable selected row."""
        selected_item = self.tree.selection()
        if selected_item:
            row_id = selected_item[0]
            if row_id in self.disabled_rows:
                # Re-enable the row and restore original alternating row color
                self.disabled_rows.remove(row_id)
            else:
                # Disable the row and color it a lighter red
                self.disabled_rows.add(row_id)
            self.apply_row_color_scheme()

    def toggle_plot_highlight(self):
        """Highlight the selected row in lighter green to indicate plotting."""
        selected_item = self.tree.selection()
        if selected_item:
            row_id = selected_item[0]
            if row_id in self.enabled_plot_rows:
                # Remove the highlight and restore original alternating row color
                self.enabled_plot_rows.remove(row_id)
            else:
                # Add the highlight with a lighter green color
                self.enabled_plot_rows.add(row_id)
            self.apply_row_color_scheme()

    def get_table_data(self):
        """Gather the current state of the table for saving."""
        data = []
        for child in self.tree.get_children():
            values = self.tree.item(child, "values")
            row_data = {col: values[i] for i, col in enumerate(self.columns)}
            row_data["disabled"] = child in self.disabled_rows
            row_data["plot"] = child in self.enabled_plot_rows
            data.append(row_data)
        return data

    def load_table_data(self, data):
        """Load table data and restore the state from saved data."""
        # Clear the current table
        for child in self.tree.get_children():
            self.tree.delete(child)

        # Insert loaded data into the table
        self.disabled_rows.clear()
        self.enabled_plot_rows.clear()

        for i, row_data in enumerate(data):
            row_values = [row_data[col] for col in self.columns]
            row_tag = "oddrow" if i % 2 == 0 else "evenrow"
            row_id = self.tree.insert("", "end", values=row_values, tags=(row_tag,))

            if row_data.get("disabled"):
                self.disabled_rows.add(row_id)
                self.tree.item(row_id, tags=("disabled",))
                self.tree.tag_configure("disabled", background="#FFB6C1")  # Lighter red

            if row_data.get("plot"):
                self.enabled_plot_rows.add(row_id)
                self.tree.item(row_id, tags=("plot",))
                self.tree.tag_configure("plot", background="#90EE90")  # Lighter green

        self.apply_row_color_scheme()


class ExpressionEditor(BaseEditor):
    def __init__(self, parent):
        super().__init__(parent, title="Expression Editor", columns=["Symbol", "Expression"], left_justify_columns=["Expression"], column_ratios=[1, 2])

class ConstraintEditor(BaseEditor):
    def __init__(self, parent):
        # Update plot button text to "Show Constraint"
        super().__init__(parent, title="Constraint Editor", columns=["Symbol", "Constraint Expression"], left_justify_columns=["Constraint Expression"], column_ratios=[1, 2], plot_button_text="Show Constraint")

class InstanceTableEditor(BaseEditor):
    def __init__(self, parent):
        # Evenly distribute the width of the columns and change button text to "Set LUTs"
        super().__init__(parent, title="Instance Table",
                         columns=["Instance Name", "kgm", "ID", "W", "L"],
                         column_ratios=[2, 1, 1, 1, 1], plot_button_text="Set LUTs")
        self.set_column_widths()
        self.bind("<Configure>", self.enforce_minimum_width)

    def set_column_widths(self):
        """Set fixed minimum column widths for the instance table."""
        self.tree.column("Instance Name", minwidth=150, width=150)
        self.tree.column("kgm", minwidth=70, width=70)
        self.tree.column("ID", minwidth=70, width=70)
        self.tree.column("W", minwidth=70, width=70)
        self.tree.column("L", minwidth=70, width=70)

    def enforce_minimum_width(self, event):
        """Ensure the table has a minimum width to prevent it from becoming too narrow."""
        min_width = 450  # Set your desired minimum width
        if self.winfo_width() < min_width:
            self.config(width=min_width)


class EditorPanedWindow(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.create_paned_window()

    def create_paned_window(self):
        """Create the paned window and add the three editors."""
        self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)  # Default PanedWindow with visible sash
        self.paned_window.grid(row=0, column=0, sticky="nsew")

        # Create and add the ExpressionEditor
        self.expression_editor = ExpressionEditor(self.paned_window)
        self.paned_window.add(self.expression_editor, weight=3)  # Give more weight to the expression editor

        # Create a sub-paned window for ConstraintEditor and InstanceTableEditor
        sub_paned_window = ttk.PanedWindow(self.paned_window, orient=tk.VERTICAL)
        self.paned_window.add(sub_paned_window, weight=1)

        # Add ConstraintEditor and InstanceTableEditor
        self.constraint_editor = ConstraintEditor(sub_paned_window)
        sub_paned_window.add(self.constraint_editor, weight=1)

        self.instance_table_editor = InstanceTableEditor(sub_paned_window)
        sub_paned_window.add(self.instance_table_editor, weight=1)

        # Add Save/Load and Open Editor buttons at the bottom
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, sticky="ew", pady=10)

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_all_data)
        self.save_button.pack(side="right", padx=5)

        self.load_button = ttk.Button(button_frame, text="Load", command=self.load_all_data)
        self.load_button.pack(side="right", padx=5)

        # Add the "Open Editor" button
        self.open_editor_button = ttk.Button(button_frame, text="Open Editor", command=self.open_editor_window)
        self.open_editor_button.pack(side="left", padx=5)

        # Configure the layout to expand with the window
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def open_editor_window(self):
        """Open a new window with the editors arranged side-by-side and stacked, and populate with the current state."""
        editor_window = tk.Toplevel(self)
        editor_window.title("Editor Window")

        # Create a paned window for the new editor layout
        paned_window = ttk.PanedWindow(editor_window, orient=tk.HORIZONTAL)
        paned_window.grid(row=0, column=0, sticky="nsew")

        # Create and add the ExpressionEditor on the left
        expression_editor = ExpressionEditor(paned_window)
        expression_editor.load_table_data(self.expression_editor.get_table_data())  # Populate with current data
        paned_window.add(expression_editor, weight=2)

        # Create a sub-paned window for the right side
        sub_paned_window = ttk.PanedWindow(paned_window, orient=tk.VERTICAL)
        paned_window.add(sub_paned_window, weight=1)

        # Add the ConstraintEditor and InstanceTableEditor on the right side
        constraint_editor = ConstraintEditor(sub_paned_window)
        constraint_editor.load_table_data(self.constraint_editor.get_table_data())  # Populate with current data
        sub_paned_window.add(constraint_editor, weight=1)

        instance_table_editor = InstanceTableEditor(sub_paned_window)
        instance_table_editor.load_table_data(self.instance_table_editor.get_table_data())  # Populate with current data
        sub_paned_window.add(instance_table_editor, weight=1)

        # Add buttons for Save, Load, and Update at the bottom
        button_frame = ttk.Frame(editor_window)
        button_frame.grid(row=1, column=0, sticky="ew", pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_all_data)
        save_button.pack(side="right", padx=5)

        load_button = ttk.Button(button_frame, text="Load", command=self.load_all_data)
        load_button.pack(side="right", padx=5)

        update_button = ttk.Button(button_frame, text="Update", command=lambda: self.update_main_window(expression_editor, constraint_editor, instance_table_editor))
        update_button.pack(side="right", padx=5)

        # Configure the editor window to resize with the content
        editor_window.columnconfigure(0, weight=1)
        editor_window.rowconfigure(0, weight=1)

    def update_main_window(self, expression_editor, constraint_editor, instance_table_editor):
        """Update the main window with data from the editor window."""
        self.expression_editor.load_table_data(expression_editor.get_table_data())
        self.constraint_editor.load_table_data(constraint_editor.get_table_data())
        self.instance_table_editor.load_table_data(instance_table_editor.get_table_data())

    def save_all_data(self):
        """Save the state of all tables into a JSON file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            # Gather data from all editors
            data = {
                "expression_editor": self.expression_editor.get_table_data(),
                "constraint_editor": self.constraint_editor.get_table_data(),
                "instance_table_editor": self.instance_table_editor.get_table_data(),
            }

            # Save to JSON
            with open(file_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            print(f"All data saved to {file_path}")

    def load_all_data(self):
        """Load the state of all tables from a JSON file."""
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)

            # Load data into all editors
            self.expression_editor.load_table_data(data.get("expression_editor", []))
            self.constraint_editor.load_table_data(data.get("constraint_editor", []))
            self.instance_table_editor.load_table_data(data.get("instance_table_editor", []))

# Create main window and instantiate the EditorPanedWindow
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Main Window")

    # Create the main paned window with horizontal orientation
    main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main_paned_window.grid(row=0, column=0, sticky="nsew")

    # Instantiate the EditorPanedWindow and add it to the left side of the main window
    editor_paned_window = EditorPanedWindow(main_paned_window)
    main_paned_window.add(editor_paned_window, weight=1)

    # Configure root window resizing
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Start the main event loop
    root.mainloop()
