import tkinter as tk
from tkinter import ttk

class CIDConstraintWidget1(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Constraint Editor")
        self.master = master

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Create expression frame inside canvas
        self.expression_frame = ttk.Frame(self.canvas)
        self.expression_frame.pack(fill="both", expand=True, side="left")
        self.frame_id = self.canvas.create_window((0, 0), window=self.expression_frame, anchor="nw")

        self.var_names = []
        self.expr_entries = []
        self.graph_entries = []
        self.entry_counter = 0
        expressions_dict = {}

        label_names = ["Expression", "Equality", "Constraint"]
        for i, label_name in enumerate(label_names):
            label = ttk.Label(self.expression_frame, text=label_name)
            label.grid(row=0, column=i, padx=5, pady=5, sticky="w")

        self.entry_counter = 1

        self.expression_frame.bind("<Configure>", lambda event: self.on_frame_configure())
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.add_constraint()

    def on_canvas_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_frame_configure(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def evaluate_constraints(self):
        print("TODO: Evaluate Expressions")

    def remove_constraint(self):
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

    def add_constraint(self):
        var_entry = ttk.Entry(self.expression_frame)
        var_entry.grid(row=self.entry_counter, column=0, padx=5, pady=5, sticky="ew")
        self.var_names.append(var_entry)

        expr_entry = ttk.Entry(self.expression_frame)
        expr_entry.grid(row=self.entry_counter, column=1, padx=5, pady=5, sticky="ew")
        self.expr_entries.append(expr_entry)

        enable_graph = ttk.Checkbutton(self.expression_frame)
        enable_graph.grid(row=self.entry_counter, column=2, padx=5, pady=5, sticky="w")
        self.graph_entries.append(enable_graph)

        self.entry_counter += 1
        self.on_frame_configure()


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
            print(canvas_width)
            print(str(e.width) + " " + str(e.height))
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
        self.entry_frames = []
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
        print("TODO: Evaluate Expressions")

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
                                         'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
        self.x_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.x_dropdown.current(21)
        self.y_label = ttk.Label(top_buttons_frame, text="Y:")
        self.y_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        #y_dropdown = ttk.Combobox(top_buttons_frame, values=["Y1", "Y2", "Y3"], width=10)
        self.y_dropdown = ttk.Combobox(top_buttons_frame, width=10)
        self.y_dropdown["values"] = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb,', 'gmidft',
                                         'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds', 'ro',
                                         'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')
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
