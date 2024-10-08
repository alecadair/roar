import numpy as np
from collections import defaultdict, deque
#import PIL
from PIL import Image, ImageTk
from cid import *
from python_code_editor import *
from python_console import *
from sympy import symbols, sympify



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
