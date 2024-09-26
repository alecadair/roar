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


class CIDEquationSolver:
    def __init__(self, lookup_vals, graph_controller, test=False):
        self.equations = {}
        self.equation_strs = {}
        self.variables = {}
        self.lookup_vals = lookup_vals
        self.graph_controller = graph_controller
        self.graph_controller_notebook = self.graph_controller.master.master
        self.data_frames = []
        self.corners = []
        self.lookup_vals = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth')

        if test:
            self.graph_controller_notebook.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130", pdk_name="sky130")
            test_corner = self.graph_controller_notebook.tech_dict["sky130"]["n_01v8"]["150"]["corners"]["nfettt-25"]
            self.corners.append(test_corner)
            print("Testing Equation Solver")

    def add_equation(self, name, equation_or_value):
        if isinstance(equation_or_value, np.ndarray):
            self.variables[name] = equation_or_value
        else:
            equation_or_value = equation_or_value.replace("+", " + ")
            equation_or_value = equation_or_value.replace("-", " - ")
            equation_or_value = equation_or_value.replace("*", " * ")
            equation_or_value = equation_or_value.replace("/", " / ")
            equation_or_value = equation_or_value.replace("(", " ( ")
            equation_or_value = equation_or_value.replace(")", " ) ")
            equation = equation_or_value
            try:
                # Preprocess the equation to handle scientific notation
                if 'e' in equation:
                    # Split the expression at 'e' and reconstruct it with '*10**' notation
                    parts = equation.split('e')
                    if len(parts) == 2:
                        equation = f"({parts[0]}*10**{parts[1]})"
                # Now, sympify the equation
                sympified_equation = sympify(equation)
                self.equations[name] = sympified_equation
                self.equation_strs[name] = str(sympified_equation)

            except Exception as e:
                print(f"Error adding equation {name}: {e}")

    @staticmethod
    def check_if_var_is_lookup(var_name, corner):
        corner_df = corner.df
        corner_keys = corner_df.keys()
        for key in corner_keys:
            if key == var_name:
                return True
        return False

    def check_if_lookup(self, var_name):
        for corner in self.corners:
            corner_df = corner.df
            is_lookup = self.check_if_var_is_lookup(var_name, corner)
            if is_lookup:
                return True
        return False

    def remove_equation(self, name):
        if name in self.equations:
            del self.equations[name]

    def modify_equation(self, name, new_equation):
        if name in self.equations:
            self.equations[name] = new_equation

    def add_variable(self, name, value):
        self.variables[name] = value

    def remove_variable(self, name):
        if name in self.variables:
            del self.variables[name]

    def create_matrix_from_lookup(self, var_name):
        column_vectors = []
        for corner in self.corners:
            df = corner.df
            if var_name in df.columns:
                column_vectors.append(df[var_name].values)
        # Stack the column vectors horizontally to form a 2D matrix
        matrix = np.column_stack(column_vectors)
        return matrix


    def evaluate_equations1(self):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None

        # Topological sort
        sorted_equations = self.topological_sort(dependency_graph)
        sorted_equations.reverse()
        results = {}
        for equation in sorted_equations:
            if equation not in self.equations:
                self.equations[equation] = "lookup"
        for equation in sorted_equations:
            #eq = None
            eq = equation
            #if equation in self.variables.keys():
            #    eq = self.variables[equation]
            #    result = self.variables[equation]
            #else:
            #    eq_is_lookup = self.check_if_lookup(equation)
            #    if eq_is_lookup:
            #        eq = self.create_matrix_from_lookup(equation)
            #        self.add_variable(equation, eq)
            #    else:
            #        eq = self.equations[equation]
            result = self.evaluate_equation(eq, results)
            if result is not None:
                results[equation] = result
            else:
                return None

        return results

    def evaluate_equation1(self, symbolic_equation, results):
        try:
            symbolic_equation = ''.join(symbolic_equation.split())  # Remove white space characters
            #for symbol in symbolic_equation:
            #    if symbol in self.lookup_vals:
            #        self.get_vector_for_variable(symbol)
            #    print(symbol)
            variables_used = set(symbol for symbol in symbolic_equation if symbol.isalpha())
            variables_dict = {**self.variables, **results}
            print("Variables:", variables_dict)
            result = eval(symbolic_equation, {}, variables_dict)
            return result
        except Exception as e:
            print("Error:", e)
            return None

    def evaluate_equations(self):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None

        sorted_equations = self.topological_sort(dependency_graph)
        sorted_equations.reverse()
        results = {}

        for equation_name in sorted_equations:
            equation = self.equations[equation_name]
            result = self.evaluate_equation(equation, results)
            if result is not None:
                results[equation_name] = result
            else:
                return None
        return results

    def evaluate_equation(self, equation, results):
        try:
            variables_dict = {**self.variables, **results}
            evaluated_equation = equation.subs(variables_dict)

            for var in equation.free_symbols:
                var_name = str(var)
                if var_name not in variables_dict:
                    if var_name in self.numpy_arrays:
                        evaluated_equation = evaluated_equation.subs(symbols(var_name), self.numpy_arrays[var_name])
                    elif var_name in self.lookup_data:
                        value = self.lookup_data[var_name]
                        if isinstance(value, np.ndarray):
                            self.numpy_arrays[var_name] = value
                        else:
                            self.variables[var_name] = value
                        evaluated_equation = evaluated_equation.subs(symbols(var_name), value)
                    else:
                        raise ValueError(f"Variable {var_name} not found in variables or lookup data.")

            result = np.array(evaluated_equation.evalf())
            return result
        except Exception as e:
            print("Error:", e)
            return None

    def get_vector_for_variable(self, variable):
        print("variable found")

    def build_dependency_graph(self):
        dependency_graph = defaultdict(set)
        #for name, equation in self.equations.items():<ss<ss
        for name, equation in self.equation_strs.items():
            #variables = set(symbol for symbol in equation.split() if symbol.isalpha())
            equation_delimiters = r"[\+\-\*/\^\(\)\s]"
            variables = set(symbol for symbol in re.split(equation_delimiters, equation) if symbol)
            for var in variables:
                if var != name and not var.isdigit() and var != "pi":
                    dependency_graph[name].add(var)
        return dependency_graph

    def has_cycle(self, graph):
        visited = set()
        stack = set()

        def dfs(node):
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for neighbor in list(graph[node]):  # Make a copy of the neighbors to avoid modifying the graph
                if dfs(neighbor):
                    return True
            stack.remove(node)
            return False

        for node in list(graph):  # Make a copy of the nodes to avoid modifying the graph
            if dfs(node):
                return True
        return False

    def topological_sort(self, graph):
        indegree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                indegree[neighbor] += 1
        queue = deque(node for node in graph if indegree[node] == 0)
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
            # Remove node from the graph to prevent revisiting it
            del graph[node]
        # Check if there are any remaining nodes in the graph (cycles)
        if graph:
            print("Error: The equations have cyclical dependencies.")
            return None

        return result

"""

# Example usage:
solver = EquationSolver()
e = np.array([2, 2, 2])
# Add equations
solver.add_equation('a', '( b + id ) ** 2')
solver.add_equation('b', '2 * gm')
solver.add_equation('id', 'gm-1')
solver.add_equation('gm', '3*e')
solver.add_equation('e', e)

# Add variables
#solver.add_variable('e', np.array([1, 2, 3]))

# Evaluate equations
results = solver.evaluate_equations()
if results is not None:
    for name, result in results.items():
        print(f'{name}: {result}')


"""

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
        print("TODO: Evaluate Constraints")

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


class CIDOptimizerSettings(ttk.Frame):
    def __init__(self, master, graph_controller, tech_browser=None, test=False):
        super().__init__(master)
        self.master = master
        self.graph_controller = graph_controller
        self.tech_browser = tech_browser
        # Top frame for buttons and dropdowns
        self.drop_down_frame = ttk.Frame(self)
        self.drop_down_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)  # Ensures it stays at the top and uses horizontal space

        self.eval_update_frame = ttk.Frame(self)
        self.eval_update_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.X)

        # Expression editor frame
        self.expression_editor_frame = ttk.Frame(self)
        self.expression_editor_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)  # Allows dynamic resizing

        # Constraint editor frame
        self.constraint_editor_frame = ttk.Frame(self)
        self.constraint_editor_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)  # Similar to expression editor

        # Add the widgets for X and Y dropdowns and buttons
        self.button_width = 10
        self.bigger_button_width = 30
        self.x_label = ttk.Label(self.drop_down_frame, text="X:")
        self.x_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.x_dropdown = ttk.Combobox(self.drop_down_frame, width=self.button_width)
        self.x_dropdown["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb', 'gmidft',
                                     'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds',
                                     'ro', 'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
        self.x_dropdown.current(21)
        self.x_dropdown.pack(side=tk.LEFT, padx=5, pady=5)

        self.y_label = ttk.Label(self.drop_down_frame, text="Y:")
        self.y_label.pack(side=tk.LEFT, padx=5, pady=2)

        self.y_dropdown = ttk.Combobox(self.drop_down_frame, width=self.button_width)
        self.y_dropdown["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb', 'gmidft',
                                     'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds',
                                     'ro', 'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
        self.y_dropdown.current(8)
        self.y_dropdown.pack(side=tk.LEFT, padx=5, pady=2)

        self.eval_button = ttk.Button(self.eval_update_frame, width=self.bigger_button_width, text="Evaluate",
                                      command=self.evaluate_expressions)
        self.eval_button.pack(side=tk.LEFT, padx=5, fill=tk.X)
        self.space_craft_button = ttk.Button(self.eval_update_frame, width=self.bigger_button_width, text="Open SpaceCraft",
                                             command=self.open_eq_window)
        self.space_craft_button.pack(side=tk.RIGHT,padx=5, fill=tk.X)
        self.update_button = ttk.Button(self.drop_down_frame, width=self.bigger_button_width, text="Update",
                                        command=self.update_graphs)
        self.update_button.pack(side=tk.LEFT, padx=5, fill=tk.X)

        self.space_ship = EquationBuilder(self.expression_editor_frame)
        self.space_ship.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)


        self.space_ship.update_scroll_region()
        print("update scroll region")
        self.master.master.master.master.master.update_idletasks()
        space_ship_label = self.space_ship.get_builder()
        space_ship_label.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        self.space_ship.update_scroll_region()

        #Add expression and constraint editor widgets
        #self.cid_expression_widget = CIDExpressionWidget(expression_editor_frame, test=test)
        #self.cid_expression_widget.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)

        #self.constraint_editor = CIDConstraintWidget(constraint_editor_frame, test=test)
        #self.constraint_editor.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)

    def get_eq_builder_closed_state(self, builder_entries):
        print("TODO")

    def evaluate_expressions(self):
        self_control_notebook = self.master
        self_optimizer_settings = self_control_notebook.master
        self_graph_controller = self_optimizer_settings.master
        #solver = CIDEquationSolver(lookup_vals=None, graph_controller=self_graph_controller, test=False)
        solver = EquationSolver()
        corners_to_eval = self.get_selected_corners()
        df_array = []
        for corner in corners_to_eval:
            df = corner.df
            df_array.append(df)
        solver.data_frames = df_array
        default_frame = None
        for entry in self.space_ship.entries:
            symbol_entry, function_entry, options_combobox, delete_button, enable_box, enable_row_var, graph_button = entry
            expr_enable_var = enable_row_var.get()
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
            print("processed expression " + variable_name)
        results = solver.evaluate_equations()
        print("TODO: Evaluate Constraints")

    def update_graphs(self):
        print("TODO")

    def open_eq_window(self):
        builder_window = EquationBuilderWindow(master=self, builder_label=self.space_ship)
        builder_label = builder_window.get_builder()
        #self.space_ship = builder_label
        builder_label.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        #self.space_ship.pack(side=tk.TOP, padx=1, pady=1, fill=tk.BOTH, expand=True)
        print("Window Opened")

    def eq_window_closed(self, builder_label):
        #self.space_ship = builder_label
        #self.space_ship.pack_forget()

        print("Window Closed")

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