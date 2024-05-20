
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter.ttk import *


from tkinter import filedialog
from tkinter import simpledialog
import sys
import os

ROAR_HOME = os.environ["ROAR_HOME"]
ROAR_LIB = os.environ["ROAR_LIB"]
ROAR_SRC = os.environ["ROAR_SRC"]
ROAR_CHARACTERIZATION = os.environ["ROAR_CHARACTERIZATION"]
ROAR_DESIGN_SCRIPTS = os.environ["ROAR_DESIGN_SCRIPTS"]


sys.path.append(ROAR_LIB + "/python/sv_ttk-2.5.4/")
sys.path.append(ROAR_LIB + "/python/ttkwidgets-0.13.0/")
sys.path.append(ROAR_LIB + "/python/schemdraw-master")
sys.path.append(ROAR_LIB + "/python/ttkthemes-3.2.2")
sys.path.append(ROAR_LIB + "/python/ecos/ecos-2.0.13")
sys.path.append(ROAR_LIB + "/python/cvx/cvxpy-1.4.3/")

#import Image, ImageTk

from ttkwidgets import CheckboxTreeview
from ttkthemes import ThemedTk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import expression_editor
from expression_editor import *
from expression_gui import *
from checkbox_list import *
from sympy import symbols, sympify

#from gui2 import CIDTechBrowser
#from gui2 import CIDGraphingWindow

class ToggleButton(ttk.Button):
    def __init__(self, master=None, **kw):
        self.state_var = kw.pop('state_var', None)
        self.toggle_color = kw.pop('toggle_color', 'blue')
        self.default_color = kw.pop('default_color', 'grey')
        super().__init__(master, **kw)
        self.configure(command=self.toggle)
        self.update_color()

    def toggle(self):
        if self.state_var is not None:
            self.state_var.set(not self.state_var.get())
        self.update_color()

    def update_color(self):
        if self.state_var is not None and self.state_var.get():
            self.configure(style='ToggleButton.On')
        else:
            self.configure(style='ToggleButton.Off')


class ToggleButtonContainer(ttk.Frame):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.state_vars = [tk.BooleanVar(self) for _ in range(4)]
        self.create_buttons()

    def create_buttons(self):
        for i in range(2):
            for j in range(2):
                state_var = self.state_vars[i*2 + j]
                button = ToggleButton(self, state_var=state_var, text=f'Button {i*2 + j + 1}',
                                       default_color='grey', toggle_color='blue', width=20)
                button.grid(row=i, column=j, sticky="nsew")
                self.columnconfigure(j, weight=1)
                self.rowconfigure(i, weight=1)





class CIDPythonIDE(ttk.PanedWindow):
    def __init__(self, parent):
        super().__init__(parent)

        self.pane_1 = ttk.Frame(self)
        self.pane_2 = ttk.Frame(self)
        #self.pane_1.grid(row=0, column=0)
        #self.pane_2.grid(row=1, column=0)

        self.add(self.pane_1, weight=1)
        self.add(self.pane_2, weight=1)

        self.text_editor = CIDPythonEditor(self.pane_1)
        self.py_console = CIDPythonConsole(self.pane_2, locals(), self.close())
        #self.py_console = CIDGraphSettings(self.pane_2)
        self.text_editor.pack(expand=True, fill="both")
        self.py_console.pack(expand=True, fill="both")

    def close(self):
        print("Closing")


class CIDTechBrowser(ttk.Frame):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self.parent = parent
        self.graphing_widget = None
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=3)
        self.columnconfigure(index=1, weight=8)
        self.rowconfigure(index=1, weight=8)
        self.columnconfigure(index=2, weight=1)
        self.rowconfigure(index=2, weight=1)
        self.scrollbar = ttk.Scrollbar(self)

        self.scrollbar.pack(side="right", fill="y")
        self.tree = CheckboxTreeview(
            self,
            #self.pane_1,
            yscrollcommand=self.scrollbar.set
        )

        self.tree_item_counter = 0
        self.tree.pack(expand=True, fill="both", side="top")
        self.tree.insert('', str(self.tree_item_counter), 'PDK', text='PDK')
        self.tree_item_counter += 1
        self.tree.bind('<Button 1>', self.select_item)
        # Following code is for applying a dark theme and style
        #self.style = ttk.Style()
        #self.style.theme_use(theme)  # Use a theme where checkboxes are available
        #self.style.configure("Dark.Treeview", foreground="white", background="black", fieldbackground="black")
        #self.style.map("Dark.Treeview", background=[('selected', 'blue')])
        #self.tree.configure(style="Dark.Treeview")
        self.tech_dict = {}

    def select_item(self, event):
        self.tree._box_click(event)
        #clicked_items = self.tree.get_checked()
        self.graphing_widget.update_graph_from_tech_browser()

    def set_graphing_widget(self, graphing_widget):
        self.graphing_widget = graphing_widget

    def add_tech_luts(self, dirname=None, pdk_name=None):
        lut_dir = ""
        pdk = ""
        if dirname == None:
            lut_dir = filedialog.askdirectory()
            pdk = simpledialog.askstring("Technology Process Name", "Enter name of process i.e. sky130, process_soi_22")
        else:
            lut_dir = dirname
            pdk = pdk_name
        self.add_tech_from_dir(dir=lut_dir, pdk_name=pdk)
        pdk_dict = self.tech_dict[pdk]
        self.tree.insert('PDK', str(self.tree_item_counter), pdk, text=pdk)
        delim = ">"
        for model in pdk_dict:
            model_dict = pdk_dict[model]
            item_str = pdk + delim + model
            self.tree.insert(pdk, str(self.tree_item_counter), item_str, text=model)
            self.tree_item_counter += 1
            for length in model_dict:
                device = model_dict[length]["device"]
                item_str_i = pdk + delim + model + delim + length
                self.tree.insert(item_str, str(self.tree_item_counter), item_str_i, text=length)
                self.tree_item_counter += 1
                for corner in device.corners:
                    item_str_j = pdk + delim + model + delim + length + delim + corner.corner_name
                    self.tree.insert(item_str_i, str(self.tree_item_counter), item_str_j, text=corner.corner_name)
                    self.tree_item_counter += 1
        return(0)

    def add_tech_from_dir(self, dir, pdk_name):
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir,filename)
            if os.path.isdir(f):
                model_name = filename
                self.create_devices_from_model_dir(pdk_name=pdk_name, model_name=model_name, model_dir=f)
        return(self.tech_dict)

    def create_devices_from_model_dir(self, pdk_name, model_name, model_dir):
        self.tech_dict[pdk_name][model_name] = {}
        for filename in os.listdir(model_dir):
            length_dir = os.path.join(model_dir, filename)
            tokens = filename.split('_')
            length = tokens[-1]
            device = CIDDevice(device_name=model_name, vdd=0.0, lut_directory=length_dir, corner_list=None)
            self.tech_dict[pdk_name][model_name][length] = {}
            self.tech_dict[pdk_name][model_name][length]["device"] = device
            self.tech_dict[pdk_name][model_name][length]["corners"] = {}
            for corner in device.corners:
                corner_name = corner.corner_name
                self.tech_dict[pdk_name][model_name][length]["corners"][corner_name] = corner
        return(self.tech_dict)


class CIDNavigationToolbar(NavigationToolbar2Tk):
    def __init__(self, canvas, window, pack_toolbar, expand_callback):
        super().__init__(canvas, window, pack_toolbar=pack_toolbar)
        # Create a custom button and add it to the toolbar
        self.expand_button = ttk.Button(self, text="Expand", command=expand_callback)
        self.expand_button.pack(side=tk.LEFT)

    def on_custom_button_click(self):
        print("Custom button clicked")

class CIDGraphingWindow(ttk.Frame):
    def __init__(self, parent, expand_callback, graph_controller):
        super().__init__(parent)
        self.graph_controller = graph_controller
        self.graphing_widget = None
        self.expand_callback = expand_callback
        self.fig, self.ax = plt.subplots()
        self.t = np.arange(0, 3, .01)
        self.ax.plot(self.t, 2 * np.sin(2 * np.pi * self.t))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.toolbar = CIDNavigationToolbar(self.canvas, self, pack_toolbar=False, expand_callback=self.expand_callback)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.xlog = False
        self.ylog = False

    def on_key_press(self, event):
        if event.key == 'l':
            if self.ylog == False:
                self.ax.set_yscale('log')
                self.ylog = True
            else:
                self.ax.set_yscale('linear')
                self.ylog = False
        if event.key == 'k':
            if self.xlog == False:
                self.ax.set_xscale('log')
                self.xlog = True
            else:
                self.ax.set_xscale('linear')
                self.xlog = False

    def update_graph_from_tech_browser(self):
        models_selected = self.graph_controller.tech_browser.tree.get_checked()
        self.ax.cla()
        self.canvas.draw()
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                      'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                      'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        color_index = 0
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[0]
            model_name = model_tokens[1]
            length = model_tokens[2]
            corner = model_tokens[3]
            cid_corner = self.graph_controller.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            param1 = self.graph_controller.graph_settings.x_dropdown.get()
            param2 = self.graph_controller.graph_settings.y_dropdown.get()
            legend_str = pdk + " " + model_name + " " + length + " " + corner
            color = color_list[color_index]
            #cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
            #                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
                                 fig1=self.fig, ax1=self.ax, color=color, legend_str=legend_str)
            color_index += 1
            if color_index >= len(color_list):
                color_index = 0
            #self.graphing_window.canvas.draw()
            self.canvas.draw()


class CIDGraphController(ttk.PanedWindow):
    def __init__(self, parent):
        super().__init__(parent, orient=tk.VERTICAL)
        self.tech_browser = CIDTechBrowser(self, theme=theme)
        #self.graph_settings = CIDGraphSettings(self)
        self.graph_settings = CIDOptimizerSettings(self)
        self.graph_settings.pack(fill=tk.BOTH, expand=True)
        #self.graph_settings.grid(row=0, column=0, sticky="nsew")
        self.graph_settings.rowconfigure(0, weight=1)
        self.add(self.tech_browser)
        self.add(self.graph_settings)
        self.graphing_widget = None
        #self.pack(fill=tk.BOTH, expand=True)


    def set_graphing_widget(self, graphing_widget):
        self.graphing_widget = graphing_widget
        self.tech_browser.graphing_widget = graphing_widget
        self.graph_settings.graphing_wiget = graphing_widget

    def add_tech_luts(self, dirname, pdk_name):
        self.tech_browser.add_tech_luts(dirname=dirname, pdk_name=pdk_name)

#class CIDApp(tk.Tk):
class CIDApp(ThemedTk):
    def __init__(self, theme):
        ThemedTk.__init__(self, theme=theme)

        self.top_level_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.top_level_pane.pack(fill=tk.BOTH, expand=True)

        self.center_pane = ttk.PanedWindow(self.top_level_pane, orient=tk.VERTICAL)
        self.center_pane.pack(fill=tk.BOTH, expand=True)

        self.left_pane = CIDGraphControlNotebook(self.top_level_pane)
        self.left_pane.pack(fill=tk.BOTH, expand=True)
        self.top_level_pane.add(self.left_pane)

        self.grid_button_widget = CIDGraphGrid(self.center_pane, graph_controllers=self.left_pane.graph_controllers)
        self.grid_button_widget.pack(fill=tk.BOTH, expand=True)

        self.top_level_pane.add(self.center_pane)
        #self.right_pane = tk.PanedWindow(self.top_level_pane, orient=tk.VERTICAL)
        #self.right_pane.pack(fill=tk.BOTH, expand=True)
        #self.top_level_pane.add(self.right_pane)

        self.ide = CIDPythonIDE(self.top_level_pane)
        self.top_level_pane.add(self.ide)
        self.center_pane.add(self.grid_button_widget)
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac", pdk_name="tsmc28_1v8")
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac", pdk_name="sky130")

        print("Window Initialized")
        # Create a vertical pane
        #self.paned_window = tk.PanedWindow(self, orient=tk.VERTICAL)
        #self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Top pane with Matplotlib graph
        #self.top_frame = ttk.Frame(self.paned_window)
        #self.paned_window.add(self.top_frame)

        #self.figure, self.ax = plt.subplots()
        #self.canvas = FigureCanvasTkAgg(self.figure, master=self.top_frame)
        #self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        #self.plot_graph()

        # Bottom pane with scrollable table
        #self.bottom_frame = ttk.Frame(self.paned_window)
        #self.paned_window.add(self.bottom_frame)

        #self.create_table()

    def plot_graph(self):
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        self.ax.plot(x, y)
        self.ax.set_xlabel('X-axis')
        self.ax.set_ylabel('Y-axis')
        self.canvas.draw()

    def create_table(self):
        # Create Treeview widget
        self.tree = ttk.Treeview(self.bottom_frame, columns=[f"Column {i}" for i in range(1, 8)], show="headings")

        # Define columns
        for i in range(1, 8):
            self.tree.column(f"Column {i}", anchor=tk.W, width=100, minwidth=100)  # Set fixed width
            self.tree.heading(f"Column {i}", text=f"Column {i}")

        # Add sample data
        for i in range(1, 101):
            values = [f"Value {i}-{j}" for j in range(1, 8)]
            self.tree.insert("", "end", text=f"Item {i}", values=values)

        # Add horizontal scrollbar
        self.horizontal_scrollbar = ttk.Scrollbar(self.bottom_frame, orient="horizontal", command=self.tree.xview)
        self.horizontal_scrollbar.pack(side="bottom", fill="x")

        # Add vertical scrollbar
        self.vertical_scrollbar = ttk.Scrollbar(self.bottom_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vertical_scrollbar.set)
        self.vertical_scrollbar.pack(side="right", fill="y")

        self.tree.pack(fill="both", expand=True)
        self.tree.config(xscrollcommand=self.horizontal_scrollbar.set)


    def update_graph_from_tech_browser(self):
        models_selected = self.tech_browser.tree.get_checked()
        self.graphing_window.ax.cla()
        self.graphing_window.canvas.draw()
        color_list = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'k-',
                      'r--', 'b--', 'g--', 'c--', 'm--', 'y--', 'k--',
                      'r-.', 'b-.', 'g-.', 'c-.', 'm-.', 'y-.', 'k-.']
        color_index = 0
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[0]
            model_name = model_tokens[1]
            length = model_tokens[2]
            corner = model_tokens[3]
            cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            #param1 = self.graph_settings.x_axis_lookup.get()
            #param2 = self.graph_settings.y_axis_lookup.get()
            param1 = self.graph_settings.x_dropdown.get()
            param2 = self.graph_settings.y_dropdown.get()
            legend_str = pdk + " " + model_name + " " + length + " " + corner
            color = color_list[color_index]
            cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
                                             fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            color_index += 1
            if color_index >= len(color_list):
                color_index = 0
            self.graphing_window.canvas.draw()


class CIDGraphGrid(ttk.Frame):
    def __init__(self, master, graph_controllers, **kwargs):
        super().__init__(master, **kwargs)

        # Initialize the grid
        self.graphing_windows = []
        self.graph_positions = []
        self.graph_controllers = graph_controllers

        graph_counter = 0
        for i in range(2):
            self.grid_rowconfigure(i, weight=1)
            for j in range(2):
                self.grid_columnconfigure(j, weight=1)
                graph = CIDGraphingWindow(self, expand_callback=lambda x=i, y=j: self.toggle_expand(x, y), graph_controller=self.graph_controllers[graph_counter])
                graph_controllers[graph_counter].set_graphing_widget(graph)
                graph.grid(row=i,column=j,sticky="nsew")
                self.graphing_windows.append(graph)
                self.graph_positions.append((i, j))
                graph_counter = graph_counter + 1
        self.expanded = False
        self.expanded_window = None

    def toggle_expand(self, row, column):
        if not self.expanded:
            for win in self.graphing_windows:
                win.grid_forget()
            self.expanded_window = self.graphing_windows[row*2+column]
            self.expanded_window.grid(row=0, column=0, rowspan=2, columnspan=2, sticky="nsew")
            self.expanded_window.toolbar.expand_button.config(text="Collapse")
            self.expanded = True
        else:
            self.expanded_window.toolbar.expand_button.config(text="Expand")
            self.expanded_window.grid_forget()
            for idx, win in enumerate(self.graphing_windows):
                original_row, original_column = self.graph_positions[idx]
                win.grid(row=original_row, column=original_column, sticky="nsew")
            self.expanded = False



class CIDGraphingGrid(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Grid Button Widget")
        self.geometry("1000x1000")

        self.grid_button_widget = CIDGraphGrid(self)
        self.grid_button_widget.pack(fill=tk.BOTH, expand=True)


class CIDGraphControlNotebook(ttk.Notebook):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.master = master
        self.graph_controllers = []
        self.create_widgets()

    def create_widgets(self):
        tab_titles = ["Upper Left", "Upper Right", "Lower Left", "Lower Right"]
        tab_counter = 0
        for i in range(0, 4):
            tab = ttk.Frame(self)
            self.add(tab, text=tab_titles[i])
            graph_controller = CIDGraphController(tab)
            graph_controller.pack(expand=True, fill="both")
            self.graph_controllers.append(graph_controller)
            tab_counter = tab_counter + 1
        self.bind("<<NotebookTabChanged>>", self.tab_changed)

    def add_tech_luts(self, dirname, pdk_name):
        for graph_controller in self.graph_controllers:
            graph_controller.add_tech_luts(dirname=dirname, pdk_name=pdk_name)

    def add_tech_from_dir(self, dir, pdk_name):
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir, filename)
            if os.path.isdir(f):
                model_name = filename
                self.create_devices_from_model_dir(pdk_name=pdk_name, model_name=model_name, model_dir=f)
        return(self.tech_dict)

    def create_devices_from_model_dir(self, pdk_name, model_name, model_dir):
        self.tech_dict[pdk_name][model_name] = {}
        for filename in os.listdir(model_dir):
            length_dir = os.path.join(model_dir, filename)
            tokens = filename.split('_')
            length = tokens[-1]
            device = CIDDevice(device_name=model_name, vdd=0.0, lut_directory=length_dir, corner_list=None)
            self.tech_dict[pdk_name][model_name][length] = {}
            self.tech_dict[pdk_name][model_name][length]["device"] = device
            self.tech_dict[pdk_name][model_name][length]["corners"] = {}
            for corner in device.corners:
                corner_name = corner.corner_name
                self.tech_dict[pdk_name][model_name][length]["corners"][corner_name] = corner
        return(self.tech_dict)


    def tab_changed(self, event):
        current_tab = self.index("current")
        print("Tab Changed to:", current_tab)

class CIDCornerSelector(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Device and Corner Selection")


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Paned Window Example")

        # Create PanedWindow
        #self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        #self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Create top and bottom frames
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        #bottom_frame = ttk.Frame(self.paned_window)
        #self.paned_window.add(top_frame)
        #self.paned_window.add(bottom_frame)

        self.cid_expression_widget = CIDExpressionWidget(top_frame)

        # Add original buttons to top frame
        x_label = ttk.Label(top_frame, text="X:")
        x_label.grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        x_dropdown = ttk.Combobox(top_frame, values=["X1", "X2", "X3"], width=10)
        x_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="nw")

        evaluate_button = ttk.Button(top_frame, text="Evaluate Expression", width=20, command=self.cid_expression_widget.evaluate_expressions)
        evaluate_button.grid(row=0, column=2, padx=5, pady=5, sticky="nw")

        y_label = ttk.Label(top_frame, text="Y:")
        y_label.grid(row=1, column=0, padx=5, pady=5, sticky="nw")

        y_dropdown = ttk.Combobox(top_frame, values=["Y1", "Y2", "Y3"], width=10)
        y_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="nw")

        add_button = ttk.Button(top_frame, text="Add Expression", width=20, command=self.cid_expression_widget.add_expression)
        add_button.grid(row=1, column=2, padx=5, pady=5, sticky="nw")

        empty_space_label = ttk.Label(top_frame, text="")
        empty_space_label.grid(row=2, column=0, padx=5, pady=5, sticky="nw")

        update_button = ttk.Button(top_frame, text="Update", width=20)
        update_button.grid(row=2, column=1, padx=5, pady=5, sticky="nw")

        remove_button = ttk.Button(top_frame, text="Remove Expression", width=20, command=self.cid_expression_widget.remove_expression)
        remove_button.grid(row=2, column=2, padx=5, pady=5, sticky="nw")

        # Add expression editor widget to top frame
        self.cid_expression_widget.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        for i in range(3):
            top_frame.rowconfigure(i, weight=1)
        for i in range(2):
            top_frame.columnconfigure(i, weight=1)
        #top_frame.columnconfigure(0, weight=1)  # Ensure the widget stretches horizontally
        #top_frame.rowconfigure(0, weight=1)  # Ensure the canvas stretches with the frame

        # Add logo to bottom frame
        #logo_label = ttk.Label(bottom_frame, text="Your Logo Here", font=("Arial", 18), foreground="blue")
        #logo_label.pack(padx=20, pady=20)

        # Add initial expression
        self.cid_expression_widget.add_expression()

        # Configure weight for resizing
        #self.paned_window.rowconfigure(0, weight=1)
        #self.paned_window.rowconfigure(1, weight=0)

class CIDPaintWidget(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=True)

        # Create horizontal scrollbar
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, expand=True)

        # Configure canvas to use scrollbars
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Bind mouse events to canvas
        self.canvas.bind("<B1-Motion>", self.draw)

        # Create a variable to store the last mouse position
        self.last_x = None
        self.last_y = None

        # Bind canvas resize to configure scroll region
        self.canvas.bind("<Configure>", self.on_canvas_configure)

    def draw(self, event):
        """Draw on the canvas when the mouse is held down."""
        x, y = event.x, event.y
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, x, y, fill="black", width=2)
        self.last_x = x
        self.last_y = y

    def clear_canvas(self):
        """Clear the canvas."""
        self.canvas.delete("all")
        self.last_x = None
        self.last_y = None

    def on_canvas_configure(self, event):
        """Update the scroll region of the canvas."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

if __name__ == "__main__":
    test_app = 0
    app = ""
    if test_app == 1:
        # Create main application window
        root = tk.Tk()
        root.title("Multiple Expression Widgets")

        # Create multiple instances of ExpressionWidget
        expression1 = CIDExpressionWidget(root)
        expression1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        #expression2 = ExpressionWidget(root)

        # Configure grid layout to allow resizing
        #root.columnconfigure(0, weight=1)
        #root.rowconfigure(0, weight=1)
        #expression1.grid(row=0, column=0, sticky="nsew")
        #expression2.grid(row=1, column=0, sticky="nsew")

        root.mainloop()

    elif test_app == 2:
        # Example usage:
        # TODO initialize equations in solver for all lookup values on CIDEquationSolver Constructor
        # constructor should add_equation for each lookup initiated with
        solver = CIDEquationSolver(["kgm", "gm", "kcgg"], None)
        e = np.array([2, 2, 2])
        # Add equations
        solver.add_equation('a', '( b + id ) ** 2')
        solver.add_equation('b', '2 * gm')
        solver.add_equation('id', 'gm-1')
        solver.add_equation('gm', '3*e')
        solver.add_equation('e', e)
        solver.add_variable('kcgg', None)
        solver.add_variable('kgm', None)
        solver.add_equation('gbw', "kgm/kcgg")
        # Add variables
        #solver.add_variable('e', np.array([1, 2, 3]))
        
        # Evaluate equations
        results = solver.evaluate_equations()
        if results is not None:
            for name, result in results.items():
                print(f'{name}: {result}')
    elif test_app == 3:
        root = tk.Tk()
        root.title("Toggle Buttons")
        style = ttk.Style()
        style.configure('ToggleButton.On', background='blue')
        style.configure('ToggleButton.Off', background='grey')

        container = ToggleButtonContainer(root)
        container.pack(fill=tk.BOTH, expand=True)

        root.mainloop()
    elif test_app == 4:
        app = MainApplication()
        app.mainloop()
    elif test_app == 5:
        root = tk.Tk()
        root.title("CIDPaintWidget Demo")
        #paint_widget = CIDExpressionWidget(root)
        paint_widget = CIDPaintWidget(root)
        paint_widget.pack(fill=tk.BOTH, expand=True)

        root.mainloop()
    else:
        theme = "arc"
        app = CIDApp(theme)
        style = ttk.Style()
        # Configure the style to use the theme
        #style.theme_use(theme)  # You can choose different themes here
        #ttk.Style().theme_use('clam')
        app.mainloop()
