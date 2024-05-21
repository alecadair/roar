import numpy as np
from collections import defaultdict, deque
#import PIL
from PIL import Image, ImageTk
from cid import *
from python_code_editor import *
from python_console import *
from sympy import symbols, sympify


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
class CIDExpressionWidget(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Expression Editor")
        self.master = master

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        #self.canvas.grid(row=0, column=0, sticky="nsew")
        # Create vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        #self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=True)

        # Create horizontal scrollbar
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        #self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Create expression frame inside canvas
        self.expression_frame = ttk.Frame(self.canvas)
        self.expression_frame.pack(fill="both", expand=True, side="left")
        #self.canvas.create_window((0, 0), window=self.expression_frame, anchor="center")
        self.canvas.create_window((0, 0), window=self.expression_frame, anchor="center")

        self.var_names = []
        self.expr_entries = []
        self.graph_entries = []
        self.entry_counter = 0
        expressions_dict = {}

        label_names = ["Variable Name", "Expression", "Graph"]
        for i, label_name in enumerate(label_names):
            label = ttk.Label(self.expression_frame, text=label_name)
            label.grid(row=0, column=i, padx=5, pady=5)

        self.entry_counter = 1

        #self.canvas.bind("<Configure>", self.on_canvas_configure)
        # Bind canvas resize to configure scrollbar
        self.expression_frame.bind("<Configure>", lambda event: self.on_frame_configure())
        self.canvas.bind("<Configure>", self.on_canvas_configure)

    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    def on_frame_configure(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        #self.canvas.configure(scrollregion=self.bbox("all"))

    def evaluate_expressions(self):
        print("TODO: Evaluate Expressions")

    def remove_expression(self):
        # Check if there are any expressions to remove
        if self.entry_counter <= 0:
            return -1
        self.var_names[-1].destroy()
        del self.var_names[-1]
        self.expr_entries[-1].destroy()
        del self.expr_entries[-1]
        self.graph_entries[-1].destroy()
        del self.graph_entries[-1]

        self.expression_frame.update_idletasks()
        self.on_frame_configure()

        self.entry_counter -= 1

    def add_expression(self):
        var_entry = ttk.Entry(self.expression_frame)
        var_entry.grid(row=self.entry_counter, column=0, padx=5, pady=5, sticky="ew")
        self.var_names.append(var_entry)

        expr_entry = ttk.Entry(self.expression_frame)
        expr_entry.grid(row=self.entry_counter, column=1, padx=5, pady=5, sticky="ew")
        self.expr_entries.append(expr_entry)

        enable_graph = ttk.Checkbutton(self.expression_frame)
        enable_graph.grid(row=self.entry_counter, column=2, padx=5, pady=5)
        self.graph_entries.append(enable_graph)

        self.entry_counter += 1

        # Update canvas scroll region
        self.on_frame_configure()

#class CIDExpressionWidget(ttk.Frame):
class CIDExpressionWidget2(ttk.LabelFrame):
    def __init__(self, master):
        #super().__init__(master)
        super().__init__(master, text="Expression Editor")
        self.master = master

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Create expression frame inside canvas
        self.expression_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")

        self.var_names = []
        self.expr_entries = []
        self.graph_entries = []
        self.entry_counter = 0
        expressions_dict = {}

        label_names = ["Variable Name", "Expression", "Graph"]
        for i, label_name in enumerate(label_names):
            label = ttk.Label(self.expression_frame, text=label_name)
            label.grid(row=0, column=i, padx=5, pady=5)
        self.entry_counter = 1

        for i in range(self.entry_counter, 2):
            var_entry = ttk.Entry(self.expression_frame)
            var_entry.grid(row=i, column=0, padx=5, pady=5, sticky="ew")
            self.var_names.append(var_entry)

            expr_entry = ttk.Entry(self.expression_frame)
            expr_entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.expr_entries.append(expr_entry)

            enable_graph = ttk.Checkbutton(self.expression_frame)
            enable_graph.grid(row=i, column=2, padx=5, pady=5)
            self.graph_entries.append(enable_graph)
            self.entry_counter = self.entry_counter + 1

        # Add button to add expression
        # Create buttons frame
        self.buttons_frame = ttk.Frame(self)
        self.buttons_frame.grid(row=self.entry_counter, column=0, sticky="ew")

        # Add buttons to add/remove expressions
        #self.add_button = ttk.Button(self.buttons_frame, text="Add Expression", command=self.add_expression)
        #self.add_button.grid(row=0, column=0, padx=5, pady=5)

        #self.remove_button = ttk.Button(self.buttons_frame, text="Remove Expression", command=self.remove_expression)
        #self.remove_button.grid(row=0, column=1, padx=5, pady=5)

        #self.evaluate_button = ttk.Button(self.buttons_frame, text="Evaluate Expression", command=self.evaluate_expressions)
        #self.evaluate_button.grid(row=0, column=2, padx=5, pady=5)




        x_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        y_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        y_scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas.config(xscrollcommand=x_scrollbar.set, yscrollcommand=y_scrollbar.set)
        #self.evaluate_button = ttk.Button(self.main_frame, text="Evaluate Expressions", command=self.add_expression)
        #self.evaluate_button.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.expression_frame.columnconfigure((0, 1, 2), weight=1)

        # Bind canvas resize to configure scrollbar
        self.expression_frame.bind("<Configure>", lambda event, canvas=self.canvas: self.on_frame_configure(canvas))


    def on_frame_configure(self, canvas):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def evaluate_expressions(self):
        print("TODO Evaluate Expressions")

    def remove_expression(self):
        # Check if there are any expressions to remove
        if self.entry_counter <= 0:
            return -1
        self.var_names[-1].destroy()
        del self.var_names[-1]
        self.expr_entries[-1].destroy()
        del self.expr_entries[-1]
        self.graph_entries[-1].destroy()
        del self.graph_entries[-1]

        self.expression_frame.update_idletasks()
        self.on_frame_configure(self.canvas)

        self.entry_counter = self.entry_counter - 1

    def add_expression(self):

        new_check_button = ttk.Checkbutton(self.expression_frame)
        var_entry = ttk.Entry(self.expression_frame)
        var_entry.grid(row=self.entry_counter, column=0, padx=5, pady=5, sticky="ew")
        self.var_names.append(var_entry)

        expr_entry = ttk.Entry(self.expression_frame)
        expr_entry.grid(row=self.entry_counter, column=1, padx=5, pady=5, sticky="ew")
        self.expr_entries.append(expr_entry)

        enable_graph = ttk.Checkbutton(self.expression_frame)
        enable_graph.grid(row=self.entry_counter, column=2, padx=5, pady=5)
        self.graph_entries.append(enable_graph)

        self.entry_counter = self.entry_counter + 1


from PIL import Image, ImageTk


class CIDGraphSettings(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Graph Settings", padding=15)
        self.graphing_widget = None
        self.graph_controller = parent
        #self.expressions_dict = {}

        self.pack(fill="both", expand=True)
        self.parent = parent

        self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        #self.parent.title("Expression Widget")
        # Create buttons frame
        self.top_frame = ttk.Frame(self.paned_window)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.settings_frame = ttk.Frame(self.top_frame)
        self.settings_frame.grid(row=0, column=0, sticky="ew")

        self.bottom_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.top_frame)
        self.paned_window.add(self.bottom_frame)
        #self.settings_frame.columnconfigure(0, weight=1)
        for i in range(3):
            self.settings_frame.grid_rowconfigure(i, weight=1)
            self.settings_frame.grid_rowconfigure(i, weight=1)

        #self.buttons_labels_frame = ttk.Frame(self)

        # Create labels for x-axis and y-axis
        self.x_axis_label = ttk.Label(self.settings_frame, text="X:")
        self.x_axis_label.grid(row=0, column=0, sticky="nw")
        self.x_axis_lookup = tk.StringVar()
        self.x_axis_choosen = ttk.Combobox(self.settings_frame, textvariable=self.x_axis_lookup, width=15)
        self.x_axis_choosen['values'] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
        self.x_axis_choosen.current(21)
        #self.x_axis_choosen.pack(side="top", anchor="w")
        self.x_axis_choosen.grid(row=0, column=1,  padx=5, pady=5, sticky="nw")

        self.evaluate_button = ttk.Button(self.settings_frame, text="Update Graphs", command=self.evaluate_expressions, width=20)
        self.evaluate_button.grid(row=0, column=2, padx=5, pady=5, sticky="nw")

        self.y_axis_label = ttk.Label(self.settings_frame, text="Y:")
        self.y_axis_label.grid(row=1, column=0, sticky="nw")
        self.y_axis_lookup = tk.StringVar()
        self.y_axis_choosen = ttk.Combobox(self.settings_frame, textvariable=self.y_axis_lookup, width=15)
        self.y_axis_choosen["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
        self.y_axis_choosen.current(8)
        self.y_axis_choosen.grid(row=1, column=1, padx=5, pady=5, sticky="nw")

        self.add_button = ttk.Button(self.settings_frame, text="Evaluate Expressions", command=self.add_expression, width=20)
        self.add_button.grid(row=1, column=2,  padx=5, pady=5, sticky="nw")

        # Create checkboxes for x-log and y-log
        #self.x_log_var = tk.BooleanVar(self)
        #self.x_log_checkbox = ttk.Checkbutton(self.settings_frame, text="X-log", variable=self.x_log_var)
        #self.x_log_checkbox.pack(side="top", padx=5, pady=5, anchor="w")
        #self.x_log_checkbox.grid(row=1, column=1, pady=(0, 10), sticky="w")


        #self.y_log_var = tk.BooleanVar(self)
        #self.y_log_checkbox = ttk.Checkbutton(self.settings_frame, text="Y-log", variable=self.y_log_var)
        #self.y_log_checkbox.pack(side="top", padx=5, pady=5, anchor="w")
        #self.y_log_checkbox.grid(row=3, column=1, pady=(0, 10), sticky="w")
        self.empty_space_label = ttk.Label(self.settings_frame, text="")
        self.empty_space_label.grid(row=2, column=0,  padx=5, pady=5, sticky="nw")

        self.update_button = ttk.Button(self.settings_frame, text="Add Expression", command=self.remove_expression, width=15)
        self.update_button.grid(row=2, column=1,  padx=5, pady=5, sticky="nw")

        self.remove_button2 = ttk.Button(self.settings_frame, text="Remove Expression", command=self.remove_expression, width=20)
        self.remove_button2.grid(row=2, column=2,  padx=5, pady=5, sticky="nw")

        self.expression_widget = CIDExpressionWidget(self.top_frame)
        self.expression_widget.grid(row=1, column=0, padx=5, pady=5, sticky="nw")

        self.logo_image = Image.open("/home/adair/Downloads/ROAR_LOGO.PNG")  # Replace "path/to/your/image.png" with the path to your image
        self.logo_image = self.logo_image.resize((300, 100))  # Resize the image to the desired dimensions
        self.logo_photo = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = ttk.Label(self.bottom_frame, image=self.logo_photo)
        self.logo_label.grid(row=4, column=0, sticky="nsew")

        self.graph_checks_frame = ttk.Frame(self.bottom_frame)
        self.graph_checks_frame.grid(row=4, column=2, sticky="ne")

        self.graph_ul = tk.BooleanVar()
        self.graph_ul_checkbox = ttk.Checkbutton(self.graph_checks_frame, variable=self.graph_ul)
        self.graph_ul_checkbox.grid(row=0, column=0, sticky="nsew")
        self.graph_ur = tk.BooleanVar()
        self.graph_ur_checkbox = ttk.Checkbutton(self.graph_checks_frame, variable=self.graph_ur)
        self.graph_ur_checkbox.grid(row=0, column=1, sticky="nsew")
        self.graph_ll = tk.BooleanVar()
        self.graph_ll_checkbox = ttk.Checkbutton(self.graph_checks_frame, variable=self.graph_ll)
        self.graph_ll_checkbox.grid(row=1, column=0, sticky="nsew")
        self.graph_lr = tk.BooleanVar()
        self.graph_lr_checkbox = ttk.Checkbutton(self.graph_checks_frame, variable=self.graph_lr)
        self.graph_lr_checkbox.grid(row=1, column=1, sticky="nsew")

        self.expression_values = []
        self.solver = None
        self.results = []

        self.lookup_vals = ['cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgds', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth']


    def evaluate_expressions(self):
        print("TODO")

    def remove_expression(self):
        print("TODO")

    def add_expression(self):
        print("TODO")

# Instantiate the CIDExpressionEditor class in a master root window
#root = tk.Tk()
#editor = CIDExpressionEditor(root)
#root.mainloop()
