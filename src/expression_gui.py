#
# Author: Alec S. Adair
# ROAR Flow Turku, Finland
#

import tkinter as tk
from tkinter import ttk
import numpy as np
from sympy import symbols, sympify, Number
from collections import defaultdict, deque
import re
from space_craft import *
from equation_solver import *
from PIL import Image, ImageTk

ROAR_HOME = os.environ["ROAR_HOME"]
ROAR_LIB = os.environ["ROAR_LIB"]
ROAR_SRC = os.environ["ROAR_SRC"]
ROAR_CHARACTERIZATION = os.environ["ROAR_CHARACTERIZATION"]
ROAR_DESIGN_SCRIPTS = os.environ["ROAR_DESIGN"]


class CIDGraphChecks(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Create a style object
        style = ttk.Style()

# Create a custom style for the Checkbutton
        style.configure('Custom.TCheckbutton',
                background='white',  # Set background color
                foreground='lightblue',   # Set text color
                font=('Arial', 12))

        self.tl = tk.BooleanVar()
        self.tl_check = ttk.Checkbutton(self, variable=self.tl, style='Custom.TCheckbutton')
        self.tl_check.grid(row=0, column=0, padx=0, pady=0, sticky="nw")

        self.tr = tk.BooleanVar()
        self.tr_check = ttk.Checkbutton(self, variable=self.tr, style='Custom.TCheckbutton')
        self.tr_check.grid(row=0, column=1, padx=0, pady=0, sticky="ne")

        self.bl = tk.BooleanVar()
        self.bl_check = ttk.Checkbutton(self, variable=self.bl, style='Custom.TCheckbutton')
        self.bl_check.grid(row=1, column=0, padx=0, pady=0, sticky="sw")

        self.br = tk.BooleanVar()
        self.br_check = ttk.Checkbutton(self, variable=self.br, style='Custom.TCheckbutton')
        self.br_check.grid(row=1, column=1, padx=0, pady=0, sticky="nw")


class CIDConstraintWidget(ttk.LabelFrame):
    def __init__(self, master, test=False):
        super().__init__(master, text="Constraint Editor")
        self.master = master

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        #self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Create expression frame inside canvas
        self.expression_frame = ttk.Frame(self.canvas)
        #self.expression_frame.pack(fill="both", expand=True, side="left")
        #self.expression_frame.pack(fill="x", expand=True, side="left")
        self.expression_frame.pack(fill="x", expand=False, side="left")

        #self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")
        self.frame_id = self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.var_names = []
        self.expr_entries = []
        self.graph_entries = []
        self.entry_frames = []
        self.entry_counter = 0
        expressions_dict = {}

        label_frame = ttk.Frame(self.expression_frame)
        label_names = ["Expression", "Equality", "Graph"]
        for i, label_name in enumerate(label_names):
            label = ttk.Label(label_frame, text=label_name)
            #label.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        label_frame.pack(side=tk.TOP, expand=False, fill=tk.X)
        self.entry_counter = 1
        #self.expression_frame.bind("<Configure>", self.on_frame_configure)
        #self.canvas.bind("<Configure>", self.on_canvas_configure)

        def resize_canvas(e):
            box_coord = self.canvas.bbox("all")
            canvas_width = self.canvas.winfo_width()
            #print(canvas_width)
            #print(str(e.width) + " " + str(e.height))
            self.canvas.configure(scrollregion=box_coord)
            self.canvas.itemconfig(self.frame_id, width=e.width)
        self.canvas.bind("<Configure>", resize_canvas)
        self.on_frame_configure = resize_canvas
        #self.canvas.bind("<Configure>", resize_canvas)
        self.add_constraint()

    def evaluate_expressions(self):
        print("TODO: Evaluate Expressions")

    def remove_constraint(self):
        if self.entry_counter <= 1:
            return -1
        if self.entry_counter <= 0:
            return -1
        self.var_names[-1].destroy()
        del self.var_names[-1]
        self.expr_entries[-1].destroy()
        del self.expr_entries[-1]
        self.graph_entries[-1].destroy()
        del self.graph_entries[-1]
        #self.expression_frame.update_idletasks()
        self.entry_frames[-1].pack_forget()
        del self.entry_frames[-1]
        #self.on_frame_configure()
        self.entry_counter -= 1
        self.expression_frame.update_idletasks()  # Ensure frame updates before resize
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_constraint(self):
        #entry_frame = ttk.Frame(self.frame_id)
        entry_frame = ttk.Frame(self.expression_frame)
        expand = True
        var_entry = ttk.Entry(entry_frame)
        #var_entry.grid(row=self.entry_counter, column=0, padx=5, pady=5, sticky="nsew")
        var_entry.pack(side=tk.LEFT, expand=expand, padx=5, pady=5, fill=tk.X)
        self.var_names.append(var_entry)

        expr_entry = ttk.Entry(entry_frame)
        #expr_entry.grid(row=self.entry_counter, column=1, padx=5, pady=5, sticky="nsew")
        expr_entry.pack(side=tk.LEFT, expand=expand, padx=5, pady=5, fill=tk.X)
        self.expr_entries.append(expr_entry)

        enable_graph = ttk.Checkbutton(entry_frame)
        #enable_graph.grid(row=self.entry_counter, column=2, padx=5, pady=5, sticky="nsew")
        enable_graph.pack(side=tk.LEFT, expand=expand, pady=5, fill=tk.X)
        self.graph_entries.append(enable_graph)

        self.entry_frames.append(entry_frame)
        entry_frame.pack(side=tk.TOP, expand=False, fill=tk.X)
        #self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entry_counter += 1
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        #self.on_frame_configure()
        #self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class CIDExpressionWidget(ttk.LabelFrame):
    def __init__(self, master, test=False):
        super().__init__(master, text="Expression Editor")
        self.master = master
        self.test = test
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        #self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        # Add and Remove buttons

        # Create expression frame inside canvas
        self.expression_frame = ttk.Frame(self.canvas)
        #self.expression_frame.pack(fill="both", expand=True, side="left")
        #self.expression_frame.pack(fill="x", expand=True, side="left")
        self.expression_frame.pack(fill="x", expand=False, side="left")

        #self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")
        self.frame_id = self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.var_names = []
        self.expr_entries = []
        self.graph_entries = []
        self.expr_enables = []
        self.entry_frames = []
        self.check_grids = []
        self.entry_counter = 0
        expressions_dict = {}

        #self.remove_expression_button = ttk.Button(self, text="Remove Expression", command=self.remove_expression)
        #self.remove_expression_button.pack(side=tk.BOTTOM, padx=5, pady=5)
        label_frame = ttk.Frame(self.expression_frame)
        self.add_expression_button = ttk.Button(label_frame, text="Add", command=self.add_expression)
        self.add_expression_button.pack(side=tk.LEFT, padx=5, fill=tk.X)

        label_names = ["Function", "Expression", "Graph"]
        for i, label_name in enumerate(label_names):
            label = ttk.Label(label_frame, text=label_name)
            #label.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        label_frame.pack(side=tk.TOP, expand=False, fill=tk.X)
        #self.expression_frame.bind("<Configure>", self.on_frame_configure)
        #self.canvas.bind("<Configure>", self.on_canvas_configure)

        def resize_canvas(e):
            box_coord = self.canvas.bbox("all")
            canvas_width = self.canvas.winfo_width()
            self.canvas.configure(scrollregion=box_coord)
            #self.expression_frame.configure(width=canvas_width)
            self.canvas.itemconfig(self.frame_id, width=e.width)

        self.canvas.bind("<Configure>", resize_canvas)
        #self.expression_frame.bind("<Configure>", resize_canvas)
        self.on_frame_configure = resize_canvas

        #self.canvas.bind("<Configure>", resize_canvas)
        self.add_expression()
        if test:
            self.add_expression()
            self.add_expression()
            self.add_expression()
            self.add_expression()
            self.add_expression()
            self.add_expression()
            self.add_expression()
            self.add_expression()

            var0 = self.var_names[0]
            var0.insert(0, "kgm")
            var1 = self.var_names[1]
            var1.insert(0, "c_load")
            var2 = self.var_names[2]
            var2.insert(0, "gbw")
            var3 = self.var_names[3]
            var3.insert(0, "ids_0")

            expr0 = self.expr_entries[0]
            expr0.insert(0, "gm/ids")
            expr1 = self.expr_entries[1]
            expr1.insert(0, "50e-15")
            expr2 = self.expr_entries[2]
            expr2.insert(0, "250e6")
            expr3 = self.expr_entries[3]
            expr3.insert(0, "2*pi*gbw*c_load/kgm")

            self.evaluate_expressions()
            print("TODO")

    def evaluate_expressions(self):
        self_control_notebook = self.master
        self_optimizer_settings = self_control_notebook.master
        self_graph_controller = self_optimizer_settings.master
        solver = CIDEquationSolver(lookup_vals=None, graph_controller=self_graph_controller, test=False)
        default_frame = None
        for i in range(self.entry_counter):
            expr_enable_var = self.expr_enables[i].get()
            if expr_enable_var == False:
                continue
            variable_name = self.var_names[i].get()
            expression = self.expr_entries[i].get()
            var_white_space = variable_name.replace(" ", "")
            expression_white_space = expression.replace(" ", "")
            if var_white_space == "" or expression_white_space == "":
                continue
            solver.add_equation(variable_name, expression)
            print("processed expression " + variable_name)
        results = solver.evaluate_equations()
        print(results)


    def remove_expression(self):
        if self.entry_counter <= 1:
            return -1 
        if self.entry_counter <= 0:
            return -1
        self.var_names[-1].destroy()
        del self.var_names[-1]
        self.expr_entries[-1].destroy()
        del self.expr_entries[-1]
        self.graph_entries[-1].destroy()
        del self.graph_entries[-1]
        #self.expression_frame.update_idletasks()
        self.entry_frames[-1].pack_forget()
        del self.entry_frames[-1]
        self.check_grids[-1].destroy()
        del self.check_grids[-1]
        #self.expr_enables[-1].destroy()
        del self.expr_enables[-1]
        #self.on_frame_configure()
        self.entry_counter -= 1
        self.expression_frame.update_idletasks()  # Ensure frame updates before resize
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_expression(self):
        #entry_frame = ttk.Frame(self.frame_id)
        entry_frame = ttk.Frame(self.expression_frame)
        expand = True
        var_entry = ttk.Entry(entry_frame)
        #var_entry.grid(row=self.entry_counter, column=0, padx=5, pady=5, sticky="nsew")
        var_entry.pack(side=tk.LEFT, expand=expand, padx=5, pady=5, fill=tk.X)
        self.var_names.append(var_entry)

        expr_entry = ttk.Entry(entry_frame)
        #expr_entry.grid(row=self.entry_counter, column=1, padx=5, pady=5, sticky="nsew")
        expr_entry.pack(side=tk.LEFT, expand=expand, padx=5, pady=5, fill=tk.X)
        self.expr_entries.append(expr_entry)

        expr_enable_var = tk.BooleanVar(value=True)
        enable_graph = ttk.Checkbutton(entry_frame, variable=expr_enable_var)
        #enable_graph.grid(row=self.entry_counter, column=2, padx=5, pady=5, sticky="nsew")
        enable_graph.pack(side=tk.LEFT, expand=expand, pady=5, fill=tk.X)
        self.graph_entries.append(enable_graph)
        self.expr_enables.append(expr_enable_var)
        check_grid = CIDGraphChecks(entry_frame)
        check_grid.pack(side=tk.RIGHT, expand=expand, pady=5, fill=tk.X)
        self.check_grids.append(check_grid)

        self.entry_frames.append(entry_frame)
        entry_frame.pack(side=tk.TOP, expand=False, fill=tk.X)
        #self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entry_counter += 1
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        #self.on_frame_configure()
        #self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class CIDOptimizerSettings(ttk.PanedWindow):
    def __init__(self, master, graph_controller, tech_browser=None, top_level_app=None, test=False):
        super().__init__(master, orient=tk.VERTICAL)
        self.master = master
        self.top_level_app = top_level_app
        self.graph_controller = graph_controller
        self.tech_browser = tech_browser
        # Top frame for buttons and dropdowns
        #self.drop_down_frame = ttk.Frame(self)
        #self.drop_down_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)  # Ensures it stays at the top and uses horizontal space

        self.expression_editor_frame = ttk.Frame(self)
        self.expression_editor_frame.pack(side=tk.TOP, padx=10, pady=5, fill=tk.BOTH, expand=True)  # Allows dynamic resizing

        self.constraint_editor_frame = ttk.Frame(self)
        self.constraint_editor_frame.pack(side=tk.TOP, padx=10, pady=5, fill=tk.BOTH, expand=True)  # Similar to expression editor

        self.device_table_frame = ttk.Frame(self)
        self.device_table_frame.pack(side=tk.TOP, padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.eval_update_frame = ttk.Frame(self.constraint_editor_frame)

        # Expression editor frame


        # Constraint editor frame

        # Add the widgets for X and Y dropdowns and buttons
        self.button_width = 10
        self.bigger_button_width = 30

        self.eval_button = ttk.Button(self.eval_update_frame, width=self.bigger_button_width, text="Evaluate",
                                      command=self.evaluate_expressions)
        self.eval_button.pack(side=tk.LEFT, padx=5, fill=tk.X)
        self.space_craft_button = ttk.Button(self.eval_update_frame, width=self.bigger_button_width, text="Open SpaceCraft",
                                             command=self.open_eq_window)
        self.space_craft_button.pack(side=tk.RIGHT, padx=5, fill=tk.X)
        #self.update_button = ttk.Button(self.drop_down_frame, width=self.bigger_button_width, text="Update",
        #                                command=self.update_graphs)
        #self.update_button.pack(side=tk.LEFT, padx=5, fill=tk.X)

        self.space_craft = CIDEquationBuilder(self.expression_editor_frame,top_level_app=self.top_level_app)
        self.space_craft.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.space_craft_label = self.space_craft.get_builder()
        #self.space_craft_label.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.space_craft.update_scroll_region()

        self.constraint_editor = CIDConstraintBuilder(self.constraint_editor_frame, top_level_app=self.top_level_app)
        self.constraint_editor.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.constraint_editor.update()

        self.device_table = CIDDeviceTable(self.device_table_frame, top_level_app=self.top_level_app)
        self.device_table.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.constraint_editor.update_scroll_region()

        #self.logo_path = ROAR_HOME + "/images/png/ROAR_LOGO.png"
        #self.logo_image = Image.open(self.logo_path)
        #self.logo_width, self.logo_height = self.logo_image.size
        #self.new_width = int(self.logo_width * 0.8)
        #self.new_height = int(self.logo_height * 0.75)
        #self.resized_image = self.logo_image.resize((self.new_width, self.new_height), Image.Resampling.LANCZOS)
        #self.photo = ImageTk.PhotoImage(self.resized_image)
        #.logo_image = tk.PhotoImage(file=self.logo_path)
        #self.logo_label = ttk.Label(self.constraint_editor_frame, image=self.photo)
        #self.logo_label.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=1, pady=5)

        self.eval_update_frame.pack(side=tk.BOTTOM, padx=1, pady=5, fill=tk.X, expand=True)
        self.add(self.expression_editor_frame)
        self.add(self.constraint_editor_frame)
        self.add(self.device_table_frame)
        #self.top_level_app.update_idletasks()

        #Add expression and constraint editor widgets
        #self.cid_expression_widget = CIDExpressionWidget(expression_editor_frame, test=test)
        #self.cid_expression_widget.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)

        #self.constraint_editor = CIDConstraintWidget(constraint_editor_frame, test=test)
        #self.constraint_editor.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)

    def get_eq_builder_closed_state(self, builder_entries):
        print("TODO")

    def evaluate_expressions(self):
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

    def update_graphs(self):
        #self.top_level_app.update_graph_from_tech_browser()
        print("legacy")

    def open_eq_window(self):
        builder_window = EquationBuilderWindow(master=self, builder_label=self.space_craft)
        builder_label = builder_window.get_builder()
        #self.space_craft = builder_label
        builder_label.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.space_craft.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)

    def eq_window_closed(self, builder_label):
        #self.space_craft = builder_label
        #self.space_craft.pack_forget()
        print("")
        #print("Window Closed")

    def get_selected_corners(self):
        models_selected = self.tech_browser.tree.get_checked()
        corner_list = []
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[0]
            model_name = model_tokens[1]
            length = model_tokens[2]
            corner = model_tokens[3]
            cid_corner = self.graph_controller.graph_control_notebook.tech_dict[pdk][model_name][length]["corners"][corner]
            corner_list.append(cid_corner)
        return corner_list

class CIDDeviceTable(ttk.LabelFrame):
    def __init__(self, master, top_level_app):
        super().__init__(master, text="Device Table")
        self.top_level_app = top_level_app
        #self.width =
        #self.height = 40
        self.top_frame = ttk.Frame(self)
        self.buttons_frame = ttk.Frame(self)

        # Add Row button on the left
        self.add_row_button = ttk.Button(self.buttons_frame, text="Add Device", command=self.add_device)
        self.add_row_button.pack(pady=0, side=tk.LEFT)  # Aligns to the left

        self.save_state_button = ttk.Button(self.buttons_frame, text="Save", command=self.save_state)
        self.load_state_button = ttk.Button(self.buttons_frame, text="Load", command=self.load_state)

        # Pack Save and Load buttons on the right
        self.load_state_button.pack(pady=0, side=tk.RIGHT)  # Align to the right
        self.save_state_button.pack(pady=0, side=tk.RIGHT)  # Align to the right

        # Pack the buttons_frame to fill the entire width of the window
        self.buttons_frame.pack(pady=0, fill=tk.X, side=tk.BOTTOM)

        self.canvas = tk.Canvas(self.top_frame, width=25, height=50)
        self.internal_frame = ttk.Frame(self.canvas)
        self.v_scrollbar = ttk.Scrollbar(self.top_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scrollbar = ttk.Scrollbar(self.top_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, padx=2, expand=True)

        self.top_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.internal_frame, anchor="nw")
        self.bind_mouse_scroll()
        self.paned_window = ttk.PanedWindow(self.internal_frame, orient=tk.HORIZONTAL)

        self.symbol_frame = ttk.Frame(self.paned_window)
        #self.function_frame = ttk.Frame(self.paned_window)

        self.paned_window.add(self.symbol_frame, weight=1)  # Symbol frame stretches
        #self.paned_window.add(self.function_frame, weight=1)  # Function frame stretches more

        self.paned_window.pack(fill=tk.BOTH, expand=True)
        self.symbol_frame.grid_columnconfigure(0, weight=1)
        #self.function_frame.grid_columnconfigure(0, weight=1)

        self.current_row = 1  # Start at 1 because row 0 is for titles
        self.num_entries = 0
        self.entries = []
        self.bind("<Configure>", self.resize_internal_frame)

        self.create_titles()
        self.add_row()

    def create_titles(self):
        """Create the title row for the grid in each column."""
        ttk.Label(self.symbol_frame, text="Device").grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        #ttk.Label(self.function_frame, text="").grid(row=0, column=0, padx=1, pady=1, sticky="ew")

    def add_device(self):
        print("TODO")

    def save_state(self):
        print("TODO")

    def load_state(self):
        print("TODO")

    def add_row(self):
        """Add a new row to the grid for symbol, function, and options."""
        symbol_entry = ttk.Entry(self.symbol_frame, width=6)
        #function_entry = ttk.Entry(self.function_frame, width=6)

        symbol_entry.grid(row=self.current_row, column=0, padx=1, pady=3.5, sticky="ew")
        #function_entry.grid(row=self.current_row, column=0, padx=1, pady=3.5, sticky="ew")

        self.entries.append((symbol_entry,))
        #self.entries.append((symbol_entry, function_entry))

        self.current_row += 1
        self.num_entries += 1
        self.update_scroll_region()

    def delete_row(self, symbol_entry, function_entry, enable_checkbox, delete_button, graph_button):
        """Delete the specific row."""
        if self.num_entries == 0:
            return 0
        # Remove widgets from the grid
        symbol_entry.grid_forget()
        function_entry.grid_forget()
        #options_combobox.grid_forget()
        enable_checkbox.grid_forget()  # Remove the checkbox widget
        delete_button.grid_forget()
        graph_button.grid_forget()
        # Remove the row from the list, excluding the IntVar (enable_row_var)
        self.entries = [(s, f, d, e, ev, g, gv) for s, f, d, e, ev, g, gv in self.entries if s != symbol_entry]
        self.num_entries -= 1

    def update_scroll_region(self, event=None):
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def resize_internal_frame(self, event):
        canvas_width = event.width - 0
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
