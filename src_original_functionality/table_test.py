import tkinter as tk
from tkinter import ttk, filedialog
import json

class BaseEditor(ttk.LabelFrame):
    """Base class for common functionality shared by ExpressionEditor and ConstraintEditor."""

    def __init__(self, parent, title, expression_column_name):
        super().__init__(parent, text=title)

        self.disabled_rows = set()
        self.enabled_plot_rows = set()

        self.expression_column_name = expression_column_name
        self.setup_widgets()
        self.create_bindings()

    def setup_widgets(self):
        """Set up the Treeview, buttons, and layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Create a custom style for Treeview to add lines between rows
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, borderwidth=1)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # Create the Treeview with two columns: Symbol and Expression
        columns = ("Symbol", self.expression_column_name)
        self.tree = ttk.Treeview(self, columns=columns, show="headings", style="Treeview")
        self.tree.heading("Symbol", text="Symbol")
        self.tree.heading(self.expression_column_name, text=self.expression_column_name)

        # Set initial column widths and make the "Expression" column stretchable
        self.tree.column("Symbol", width=100, anchor="center", stretch=False)
        self.tree.column(self.expression_column_name, width=300, anchor="w", stretch=True)  # Left-align with anchor="w"

        # Create vertical scrollbar
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)

        # Pack the Treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")

        # Define alternating row colors
        self.tree.tag_configure('oddrow', background="white")
        self.tree.tag_configure('evenrow', background="lightgray")
        self.tree.tag_configure('disabledrow', background="lightcoral", foreground="gray")  # Disabled rows
        self.tree.tag_configure('enabled_plot', background="lightgreen")  # Enabled for plot rows

        # Initialize the table with one empty row
        self.add_row()

        # Label to show selected row
        self.selected_row_label = ttk.Label(self, text="Selected Item: None")
        self.selected_row_label.grid(row=1, column=0, columnspan=2, pady=5)

        # Create a frame for the buttons at the bottom
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        # Enable Plot Button (disabled until a row is selected)
        self.plot_button = ttk.Button(button_frame, text="Enable Plot", command=self.enable_plot, state="disabled")
        self.plot_button.pack(side="left", padx=5)

        # Disable/Enable Button for editing the selected row
        self.toggle_edit_button = ttk.Button(button_frame, text="Disable/Enable Row", command=self.toggle_row_edit, state="disabled")
        self.toggle_edit_button.pack(side="left", padx=5)

        # Add Row Button
        self.add_row_button = ttk.Button(button_frame, text="Add Row", command=self.add_row)
        self.add_row_button.pack(side="left", padx=5)

        # Delete Row Button (disabled until a row is selected)
        self.delete_button = ttk.Button(button_frame, text="Delete Selected Row", command=self.delete_row, state="disabled")
        self.delete_button.pack(side="left", padx=5)

        # Save and Load Buttons
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_table)
        self.save_button.pack(side="left", padx=5)

        self.load_button = ttk.Button(button_frame, text="Load", command=self.load_table)
        self.load_button.pack(side="left", padx=5)

    def create_bindings(self):
        """Create the necessary event bindings."""
        # Bind the double-click event to enable cell editing
        self.tree.bind("<Double-1>", self.on_double_click)

        # Bind row selection to display a button for actions
        self.tree.bind("<<TreeviewSelect>>", self.on_row_selected)

    def on_double_click(self, event):
        """Handle double-click event to enable cell editing if the row is enabled."""
        region = self.tree.identify("region", event.x, event.y)
        row_id = self.tree.identify_row(event.y)

        if row_id not in self.disabled_rows and region == "cell":
            column = self.tree.identify_column(event.x)

            # Get the column index and text
            col_index = int(column.replace('#', '')) - 1
            cell_value = self.tree.item(row_id, 'values')[col_index]

            # Create an Entry widget for editing
            x, y, width, height = self.tree.bbox(row_id, column)
            entry = tk.Entry(self, width=width // 10)
            entry.place(x=x + self.tree.winfo_x(), y=y + self.tree.winfo_y(), width=width, height=height)
            entry.insert(0, cell_value)
            entry.focus()

            def save_value(event):
                new_value = entry.get()
                current_values = list(self.tree.item(row_id, 'values'))
                current_values[col_index] = new_value
                self.tree.item(row_id, values=current_values)
                entry.destroy()

            entry.bind('<Return>', save_value)
            entry.bind('<FocusOut>', lambda e: entry.destroy())

    def toggle_row_edit(self):
        """Enable or disable the selected row for editing."""
        selected_item = self.tree.focus()
        if selected_item:
            current_values = self.tree.item(selected_item, 'values')
            if selected_item in self.disabled_rows:
                # Enable the row for editing
                self.disabled_rows.remove(selected_item)
                # Restore alternating row color
                row_index = list(self.tree.get_children()).index(selected_item)
                tag = "evenrow" if row_index % 2 == 0 else "oddrow"
                self.tree.item(selected_item, values=current_values, tags=(tag,))
            else:
                # Disable the row for editing
                self.disabled_rows.add(selected_item)
                # Mark the row as disabled
                self.tree.item(selected_item, values=current_values, tags=("disabledrow",))

    def enable_plot(self):
        """Toggle green highlight for the selected row (enable for plotting)."""
        selected_item = self.tree.focus()
        if selected_item:
            if selected_item in self.enabled_plot_rows:
                self.enabled_plot_rows.remove(selected_item)
                row_index = list(self.tree.get_children()).index(selected_item)
                tag = "evenrow" if row_index % 2 == 0 else "oddrow"
                self.tree.item(selected_item, tags=(tag,))
            else:
                self.enabled_plot_rows.add(selected_item)
                self.tree.item(selected_item, tags=("enabled_plot",))

    def on_row_selected(self, event):
        """Handler for when a row is selected in the Treeview."""
        selected_item = self.tree.focus()
        if selected_item:
            item_values = self.tree.item(selected_item, 'values')
            self.selected_row_label.config(text=f"Selected Item: {item_values}")
            self.plot_button.config(state="normal")
            self.toggle_edit_button.config(state="normal")
            self.delete_button.config(state="normal")

    def add_row(self):
        """Add a new empty row to the Treeview."""
        # Determine the last row's tag to alternate the new row color
        children = self.tree.get_children()
        if children:
            last_row_id = children[-1]
            last_row_tag = self.tree.item(last_row_id, 'tags')[0]
            new_tag = "evenrow" if last_row_tag == "oddrow" else "oddrow"
        else:
            new_tag = "oddrow"  # First row is always oddrow

        # Insert a new empty row with the alternating color
        self.tree.insert("", "end", values=("", ""), tags=(new_tag,))

    def delete_row(self):
        """Delete the selected row from the Treeview."""
        selected_item = self.tree.selection()
        if selected_item:
            # Get the index of the selected row
            row_index = list(self.tree.get_children()).index(selected_item[0])

            # Delete the row
            self.tree.delete(selected_item)
            self.disabled_rows.discard(selected_item[0])
            self.enabled_plot_rows.discard(selected_item[0])

            # Reapply alternating colors to rows below the deleted row
            self.reapply_alternating_colors(start=row_index)

    def reapply_alternating_colors(self, start):
        """Reapply alternating row colors starting from the given index."""
        rows = self.tree.get_children()
        for i in range(start, len(rows)):
            row_id = rows[i]
            if row_id in self.disabled_rows:
                self.tree.item(row_id, tags=("disabledrow",))
            elif row_id in self.enabled_plot_rows:
                self.tree.item(row_id, tags=("enabled_plot",))
            else:
                # Reapply alternating row colors
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                self.tree.item(row_id, tags=(tag,))

    def save_table(self):
        """Save the current state of the table to a JSON file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            # Gather the table data
            data = []
            for child in self.tree.get_children():
                values = self.tree.item(child, "values")
                is_disabled = child in self.disabled_rows
                is_plot_enabled = child in self.enabled_plot_rows
                data.append({
                    "symbol": values[0],
                    "expression": values[1],
                    "is_disabled": is_disabled,
                    "is_plot_enabled": is_plot_enabled
                })

            # Save to JSON
            with open(file_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            print(f"Table saved to {file_path}")

    def load_table(self):
        """Load the table state from a JSON file."""
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            # Load from JSON
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)

            # Clear the current table
            for child in self.tree.get_children():
                self.tree.delete(child)
            self.disabled_rows.clear()
            self.enabled_plot_rows.clear()

            # Insert loaded data into the table
            for i, row in enumerate(data):
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                row_id = self.tree.insert("", "end", values=(row["symbol"], row["expression"]), tags=(tag,))
                if row["is_disabled"]:
                    self.disabled_rows.add(row_id)
                    self.tree.item(row_id, tags=("disabledrow",))
                if row["is_plot_enabled"]:
                    self.enabled_plot_rows.add(row_id)
                    self.tree.item(row_id, tags=("enabled_plot",))
            print(f"Table loaded from {file_path}")

# Expression Editor class inheriting from BaseEditor
class ExpressionEditor(BaseEditor):
    def __init__(self, parent):
        super().__init__(parent, title="Expression Editor", expression_column_name="Expression")

# Constraint Editor class inheriting from BaseEditor
class ConstraintEditor(BaseEditor):
    def __init__(self, parent):
        super().__init__(parent, title="Constraint Editor", expression_column_name="Constraint Expression")

# Create main window and add the ExpressionEditor and ConstraintEditor to a PanedWindow
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Editor Paned Window")

    # Create a PanedWindow to hold both editors
    paned_window = ttk.PanedWindow(root, orient=tk.VERTICAL)
    paned_window.grid(row=0, column=0, sticky="nsew")

    # Create and add the ExpressionEditor (takes more space)
    expression_editor = ExpressionEditor(paned_window)
    paned_window.add(expression_editor, weight=2)  # More vertical space

    # Create and add the ConstraintEditor (takes less space)
    constraint_editor = ConstraintEditor(paned_window)
    paned_window.add(constraint_editor, weight=1)  # Less vertical space

    # Configure root window to expand both vertically and horizontally
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Start the main event loop
    root.mainloop()
