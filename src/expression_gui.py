#
# Author: Alec S. Adair
# ROAR Flow Turku, Finland
#

import tkinter as tk
from tkinter import ttk
from collections import defaultdict, deque
import numpy as np


class CIDEquationSolver:
    def __init__(self, lookup_vals, graph_controller):
        self.equations = {}
        self.variables = {}
        self.lookup_vals = lookup_vals
        self.graph_controller = graph_controller

    def add_equation1(self, name, equation):
        self.equations[name] = equation

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
            self.equations[name] = equation_or_value

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

    def evaluate_equations(self):
        dependency_graph = self.build_dependency_graph()
        if self.has_cycle(dependency_graph):
            print("Error: The equations have cyclical dependencies.")
            return None

        # Topological sort
        sorted_equations = self.topological_sort(dependency_graph)
        sorted_equations.reverse()
        results = {}
        for equation in sorted_equations:
            eq = ""
            if equation in self.variables.keys():
                eq = self.variables[equation]
                result = self.variables[equation]
            else:
                eq = self.equations[equation]
                result = self.evaluate_equation(eq, results)
            if result is not None:
                results[equation] = result
            else:
                return None

        return results

    def evaluate_equation(self, symbolic_equation, results):
        try:
            symbolic_equation = ''.join(symbolic_equation.split())  # Remove white space characters
            for symbol in symbolic_equation:
                if symbol in self.lookup_vals:
                    self.get_vector_for_variable(symbol)
                print(symbol)
            #variables_used = set(symbol for symbol in symbolic_equation if symbol.isalpha())
            #symbolic_equation.replace("+", " + ")
            variables_dict = {**self.variables, **results}
            #print("Variables:", variables_dict)
            result = eval(symbolic_equation, {}, variables_dict)
            return result
        except Exception as e:
            print("Error:", e)
            return None

    def get_vector_for_variable(self, variable):
        print("variable found")

    def build_dependency_graph(self):
        dependency_graph = defaultdict(set)
        for name, equation in self.equations.items():
            variables = set(symbol for symbol in equation.split() if symbol.isalpha())
            for var in variables:
                if var != name:
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
    def __init__(self, master):
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
    def __init__(self, master):
        super().__init__(master, text="Expression Editor")
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
        self.expr_enables = []
        self.entry_frames = []
        self.check_grids = []
        self.entry_counter = 0
        expressions_dict = {}

        label_frame = ttk.Frame(self.expression_frame)
        label_names = ["Function", "Expression", "Graph"]
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
            self.canvas.configure(scrollregion=box_coord)
            #self.expression_frame.configure(width=canvas_width)
            self.canvas.itemconfig(self.frame_id, width=e.width)

        self.canvas.bind("<Configure>", resize_canvas)
        #self.expression_frame.bind("<Configure>", resize_canvas)
        self.on_frame_configure = resize_canvas

        #self.canvas.bind("<Configure>", resize_canvas)
        self.add_expression()

    def evaluate_expressions(self):

        solver = CIDEquationSolver(lookup_vals=None, graph_controller=None)
        default_frame = None
        for i in range(self.entry_counter):
            expr_enable_var = self.expr_enables[i].get()
            if expr_enable_var == False:
                continue
            variable_name = self.var_names[i].get()
            expression = self.expr_entries[i].get()
            solver.add_equation(variable_name, expression)
            print("processed expression" + variable_name)
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
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        top_buttons_frame = ttk.Frame(self)
        expression_editor_frame = ttk.Frame(self)

        expression_editor_buttons_frame = ttk.Frame(self)
        constraint_editor_frame = ttk.Frame(self)
        constraint_editor_buttons_frame = ttk.Frame(self)

        constraint_editor_buttons_frame.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)
        constraint_editor_frame.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)
        expression_editor_buttons_frame.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)
        expression_editor_frame.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)
        top_buttons_frame.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)

        button_width = 10

        self.cid_expression_widget = CIDExpressionWidget(expression_editor_frame)
        self.cid_expression_widget.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)

        self.constraint_editor = CIDConstraintWidget(constraint_editor_frame)
        self.constraint_editor.pack(side=tk.BOTTOM, padx=5, pady=5, expand=True, fill=tk.BOTH)

        self.x_label = ttk.Label(top_buttons_frame, text="X:")
        self.x_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        #x_dropdown = ttk.Combobox(top_buttons_frame, values=["X1", "X2", "X3"], width=10)
        self.x_dropdown = ttk.Combobox(top_buttons_frame, width=10)
        self.x_dropdown["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth')
        self.x_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.x_dropdown.current(21)
        self.y_label = ttk.Label(top_buttons_frame, text="Y:")
        self.y_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        #y_dropdown = ttk.Combobox(top_buttons_frame, values=["Y1", "Y2", "Y3"], width=10)
        self.y_dropdown = ttk.Combobox(top_buttons_frame, width=10)
        self.y_dropdown["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth')
        self.y_dropdown.current(8)
        self.y_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        #empty_space_label = ttk.Label(top_buttons_frame, text="")
        #empty_space_label.grid(row=2, column=0, padx=5, pady=5, sticky="nw")

        self.update_button = ttk.Button(top_buttons_frame, text="Update", width=20)
        self.update_button.grid(row=1, column=2, padx=5, pady=5, sticky="nw")

        self.add_expression_button = ttk.Button(expression_editor_buttons_frame, text="Add", width=button_width, command=self.cid_expression_widget.add_expression)
        self.add_expression_button.pack(side=tk.LEFT, padx=5, pady=5, expand=False)

        self.remove_expression_button = ttk.Button(expression_editor_buttons_frame, text="Remove", width=button_width, command=self.cid_expression_widget.remove_expression)
        self.remove_expression_button.pack(side=tk.LEFT, padx=5, pady=5, expand=False)

        self.add_constraint_button = ttk.Button(constraint_editor_buttons_frame, text="Add", width=button_width, command=self.constraint_editor.add_constraint)
        self.add_constraint_button.pack(side=tk.LEFT, padx=5, pady=5, expand=False)

        self.remove_constraint_button = ttk.Button(constraint_editor_buttons_frame, text="Remove", width=button_width, command=self.constraint_editor.remove_constraint)
        self.remove_constraint_button.pack(side=tk.LEFT, padx=5, pady=5, expand=False)


        self.evaluate_button = ttk.Button(constraint_editor_buttons_frame, text="Evaluate", width=button_width*2, command=self.cid_expression_widget.evaluate_expressions)
        self.evaluate_button.pack(side=tk.RIGHT, padx=5, pady=5, expand=False)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
