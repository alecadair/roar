import tkinter as tk
from tkinter import ttk, filedialog
import json
from equation_solver import *
from gui4 import *

class BaseEditor(ttk.LabelFrame):
    def __init__(self, parent, title, columns, left_justify_columns=None, column_ratios=None,
                 plot_button_text="Add LUT", plot_command=None):
        super().__init__(parent, text=title)
        self.columns = columns
        self.left_justify_columns = left_justify_columns if left_justify_columns else []
        self.column_ratios = column_ratios if column_ratios else [1] * len(columns)  # Default ratio of 1:1 for columns
        self.plot_button_text = plot_button_text
        self.disabled_rows = set()
        self.enabled_plot_rows = set()
        self.plot_command = plot_command
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
        self.add_button.pack(side="left", padx=2, fill=tk.BOTH, expand=True)

        self.delete_button = ttk.Button(button_frame_1, text="-", command=self.delete_row)
        self.delete_button.pack(side="left", padx=2, fill=tk.BOTH, expand=True)

        self.enable_disable_button = ttk.Button(button_frame_1, text="Enable/Disable", command=self.toggle_enable_disable_row)
        self.enable_disable_button.pack(side="left", padx=2, fill=tk.BOTH, expand=True)

        self.plot_button = ttk.Button(button_frame_1, text=self.plot_button_text, command=self.plot_command)
        self.plot_button.pack(side="left", padx=2, fill=tk.BOTH, expand=True)

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
    def __init__(self, parent, plot_command=None, top_level_app=None):
        super().__init__(parent, title="Expression Editor", columns=["Symbol", "Expression"], left_justify_columns=["Expression"],
                         column_ratios=[1, 2], plot_command=plot_command)
        self.plot_command = plot_command
        self.top_level_app = top_level_app


class ConstraintEditor(BaseEditor):
    def __init__(self, parent, plot_command=None, top_level_app=None):
        # Update plot button text to "Show Constraint"
        super().__init__(parent, title="Constraint Editor", columns=["Symbol", "Constraint Expression"],
                         left_justify_columns=["Constraint Expression"], column_ratios=[1, 2],
                         plot_button_text="Show Constraint", plot_command=plot_command)
        self.plot_command = plot_command
        self.top_level_app = top_level_app


class CIDInstanceTable(BaseEditor):
    def __init__(self, parent, top_level_app):
        # Evenly distribute the width of the columns and change button text to "Set LUTs"
        super().__init__(parent, title="Instance Table",
                         columns=["Instance Name", "kgm", "ID", "W", "L"],
                         column_ratios=[2, 1, 1, 1, 1], plot_button_text="Set LUTs", plot_command=self.set_device_luts_from_tech_browser)
        self.top_level_app = top_level_app
        self.set_column_widths()
        #self.plot_command = plot_command
        #self.bind("<Configure>", self.enforce_minimum_width)

    def get_instance_names(self):
        """Retrieve all instance names from the Instance Table Editor."""
        instance_names = []

        # Iterate over all rows in the treeview
        for row_id in self.tree.get_children():
            row_values = self.tree.item(row_id)['values']  # Get the values of the row
            instance_name = row_values[0]  # Assuming 'Instance Name' is in the first column
            instance_names.append(instance_name)

        return instance_names

    def set_device_luts_from_tech_browser(self):
        """Open a new window with a CIDTechBrowser and a Select button, populated with the same tree structure."""

        # Step 1: Open a new window
        tech_window = tk.Toplevel(self)
        tech_window.title("LUT Selection")
        tech_window.attributes("-topmost", True)

        # Focus the window so that it is ready for user interaction
        tech_window.focus()
        original_tech_browser = self.top_level_app.graph_grid.lookup_windows[0].tech_browser

        # Step 2: Instantiate a new CIDTechBrowser
        tech_browser = CIDTechBrowser(tech_window, lookup_window=None, top_level_app=self.top_level_app)
        tech_browser.pack(side="top", fill="both", expand=True)

        # Step 3: Get the existing tech_browser from CIDLookupWindow in the Grid object
        # Step 4: Copy the tree structure from the original tech browser to the new one
        self.copy_tech_browser_tree(original_tech_browser, tech_browser)

        # Step 5: Add a Select button
        select_button = ttk.Button(tech_window, text="Select", command=lambda: self.get_corners_from_tech_browser(tech_browser, tech_window))
        select_button.pack(side="top", pady=3, expand=True, fill=tk.X)

        # Configure the new window to stretch with content
        tech_window.columnconfigure(0, weight=1)
        tech_window.rowconfigure(0, weight=1)

    def copy_tech_browser_tree(self, original_tech_browser, new_tech_browser):
        """Copy the tree structure from the original tech_browser to the new tech_browser."""

        # Clear all nodes from the new tech browser's treeview
        new_tech_browser.tree.delete(*new_tech_browser.tree.get_children())

        # Get the tree data from the original tech browser
        original_tree = original_tech_browser.tree
        for parent_node in original_tree.get_children():
            # Recursively copy all nodes from the original tree to the new tree
            self.copy_tree_node(original_tree, new_tech_browser.tree, parent_node, "")


    def copy_tree_node(self, original_tree, new_tree, node, parent):
        """Recursively copy a tree node and its children."""
        # Get the node's text (this is the label shown in the treeview)
        node_text = original_tree.item(node, 'text')
        node_values = original_tree.item(node, 'values')

        # Insert the node into the new tree with the same text and values
        new_node = new_tree.insert(parent, 'end', text=node_text, values=node_values)

        # Recursively copy the children nodes
        for child_node in original_tree.get_children(node):
            self.copy_tree_node(original_tree, new_tree, child_node, new_node)

    def get_corners_from_tech_browser(self, tech_browser, tech_window):
        """Retrieve the selected corners from the TechBrowser."""
        # Call the get_selected_corners method to retrieve the CIDCorners list
        #cid_corners = tech_browser.get_selected_corners()
        models_selected = tech_browser.get_selected_corners()
        corner_list = []
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[1]
            model_name = model_tokens[2]
            length = model_tokens[3]
            corner = model_tokens[4]
            cid_corner = self.top_level_app.tech_dict[pdk][model_name][length]["corners"][corner]
            corner_list.append(cid_corner)
        #return corner_list
        # Close the tech window after selection
        tech_window.destroy()
        # Now process the CIDCorners list as required
        print("Selected Corners:", models_selected)
        # Continue working with the CIDCorners list as needed


    def set_column_widths(self):
        """Set fixed minimum column widths for the instance table."""
        self.tree.column("Instance Name", minwidth=150, width=150)
        self.tree.column("kgm", minwidth=70, width=70)
        self.tree.column("ID", minwidth=70, width=70)
        self.tree.column("W", minwidth=70, width=70)
        self.tree.column("L", minwidth=70, width=70)

    def enforce_minimum_width(self, event):
        """Ensure the table has a minimum width to prevent it from becoming too narrow."""
        min_width = 700  # Set your desired minimum width
        if self.winfo_width() < min_width:
            self.config(width=min_width)


class EditorPanedWindow(ttk.Frame):

    def __init__(self, parent, top_level_app=None):
        super().__init__(parent)
        self.top_level_app = top_level_app
        self.create_paned_window()

    def create_paned_window(self):
        """Create the paned window and add the three editors."""
        self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)  # Default PanedWindow with visible sash
        self.paned_window.grid(row=0, column=0, sticky="nsew")

        # Create and add the ExpressionEditor
        self.expression_editor = ExpressionEditor(self.paned_window, top_level_app=self.top_level_app)
        self.paned_window.add(self.expression_editor, weight=3)  # Give more weight to the expression editor

        # Create a sub-paned window for ConstraintEditor and CIDInstanceTable
        sub_paned_window = ttk.PanedWindow(self.paned_window, orient=tk.VERTICAL)
        self.paned_window.add(sub_paned_window, weight=1)

        # Add ConstraintEditor and CIDInstanceTable
        self.constraint_editor = ConstraintEditor(sub_paned_window, top_level_app=self.top_level_app)
        sub_paned_window.add(self.constraint_editor, weight=1)

        self.instance_table = CIDInstanceTable(sub_paned_window, top_level_app=self.top_level_app)
        sub_paned_window.add(self.instance_table, weight=1)

        # Add Save/Load and Open Editor buttons at the bottom
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, sticky="ew", pady=10)

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_all_data)
        self.save_button.pack(side="right", padx=3)

        self.load_button = ttk.Button(button_frame, text="Load", command=self.load_all_data)
        self.load_button.pack(side="right", padx=3)
        self.evaluate_button =ttk.Button(button_frame, text="Evaluate", command=self.evaluate_expressions)
        self.evaluate_button.pack(side="left", fill=tk.X)
        # Add the "Open Editor" button
        self.open_editor_button = ttk.Button(button_frame, text="Open Editor", command=self.open_editor_window)
        self.open_editor_button.pack(side="left", padx=5)

        # Configure the layout to expand with the window
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)


    def evaluate_expressions(self):
        instances = self.instance_table.get_instance_names()
        devices = []
        for inst in instances:
            print("TODO")
        print("")
        print("Evaluating Expressions")
        self_control_notebook = self.master
        self_optimizer_settings = self_control_notebook.master
        #solver = CIDEquationSolver(lookup_vals=None, graph_controller=self_graph_controller, test=False)
        solver = EquationSolver(top_level_app=self.top_level_app)
        corners_to_eval = self.get_selected_corners()
        df_array = []
        symbols_to_add = []
        for corner in corners_to_eval:
            df = corner.df
            df_array.append(df)
        solver.corners = corners_to_eval
        default_frame = None
        for entry in self.space_craft.entries:
            symbol_entry, function_entry, delete_button, enable_box, enable_row_var, graph_button, graph_var = entry
            expr_enable_var = enable_row_var.get()
            plot_enable = graph_var.get()
            if expr_enable_var == False:
                continue
            variable_name = symbol_entry.get()
            expression = function_entry.get()
            expression = expression.replace("pi", "3.141592653589793")
            var_white_space = variable_name.replace(" ", "")
            expression_white_space = expression.replace(" ", "")
            if var_white_space == "" or expression_white_space == "":
                continue
            solver.add_equation(variable_name, expression)
            if plot_enable:
                symbols_to_add.append(symbol_entry)
                if symbol_entry not in self.top_level_app.lookups:
                    self.top_level_app.lookups = self.top_level_app.lookups + (symbol_entry.get(),)
            print("processed expression " + variable_name)
        results = solver.evaluate_equations(symbols_to_add)
        self.x_dropdown["values"] = self.top_level_app.lookups
        #self.x_dropdown.current(self.x_dropdown.get())

        self.y_dropdown["values"] = self.top_level_app.lookups
        #self.y_dropdown.current(self.y_dropdown.get())

        print("")
        print(results)

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

        # Add the ConstraintEditor and CIDInstanceTable on the right side
        constraint_editor = ConstraintEditor(sub_paned_window)
        constraint_editor.load_table_data(self.constraint_editor.get_table_data())  # Populate with current data
        sub_paned_window.add(constraint_editor, weight=1)

        instance_table = CIDInstanceTable(sub_paned_window)
        instance_table.load_table_data(self.instance_table.get_table_data())  # Populate with current data
        sub_paned_window.add(instance_table, weight=1)

        # Add buttons for Save, Load, and Update at the bottom
        button_frame = ttk.Frame(editor_window)
        button_frame.grid(row=1, column=0, sticky="ew", pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_all_data)
        save_button.pack(side="right", padx=5)

        load_button = ttk.Button(button_frame, text="Load", command=self.load_all_data)
        load_button.pack(side="right", padx=5)

        update_button = ttk.Button(button_frame, text="Update", command=lambda: self.update_main_window(expression_editor, constraint_editor, instance_table))
        update_button.pack(side="right", padx=5)

        # Configure the editor window to resize with the content
        editor_window.columnconfigure(0, weight=1)
        editor_window.rowconfigure(0, weight=1)

    def update_main_window(self, expression_editor, constraint_editor, instance_table):
        """Update the main window with data from the editor window."""
        self.expression_editor.load_table_data(expression_editor.get_table_data())
        self.constraint_editor.load_table_data(constraint_editor.get_table_data())
        self.instance_table.load_table_data(instance_table.get_table_data())

    def save_all_data(self):
        """Save the state of all tables into a JSON file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            # Gather data from all editors
            data = {
                "expression_editor": self.expression_editor.get_table_data(),
                "constraint_editor": self.constraint_editor.get_table_data(),
                "instance_table": self.instance_table.get_table_data(),
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
            self.instance_table.load_table_data(data.get("instance_table", []))

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
