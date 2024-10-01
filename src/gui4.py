
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter.ttk import *


from tkinter import filedialog
from tkinter import simpledialog
import sys
import os
import signal

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

class CIDTechBrowser2(ttk.Frame):
    def __init__(self, parent, top_level_app):
        super().__init__(parent)
        self.parent = parent
        self.top_level_app = top_level_app
        self.graphing_widget = None
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=3)
        self.columnconfigure(index=1, weight=8)
        self.rowconfigure(index=1, weight=8)
        self.columnconfigure(index=2, weight=1)
        self.rowconfigure(index=2, weight=1)
        self.scrollbar = ttk.Scrollbar(self)
        #self.graph_controller = graph_controller
        self.scrollbar.pack(side="right", fill="y")
        self.tree = CheckboxTreeview(
            self,
            #self.pane_1,
            yscrollcommand=self.scrollbar.set
        )

        self.tree_item_counter = 0
        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.TOP)
        self.tree.insert('', str(self.tree_item_counter), 'PDK', text='PDK')
        self.tree_item_counter += 1
        self.tree.bind('<Button 1>', self.select_item)
        self.tech_dict = {}

    def select_item(self, event):
        self.tree._box_click(event)
        #clicked_items = self.tree.get_checked()
        self.parent.update_graph_from_tech_browser()

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
        #self.add_tech_from_dir(dir=lut_dir, pdk_name=pdk)
        #pdk_dict = self.tech_dict[pdk]
        self.tree.insert('PDK', str(self.tree_item_counter), pdk, text=pdk)
        #tech_dict = self.graph_controller.graph_control_notebook.tech_dict
        pdk_dict = self.top_level_app.tech_dict[pdk_name]
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
        self.add_tech_luts(dirname=dir, pdk_name=pdk_name)
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


class CIDTechBrowser(ttk.Frame):
    def __init__(self, parent, graph_controller, theme=None):
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
        self.graph_controller = graph_controller
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
        #self.add_tech_from_dir(dir=lut_dir, pdk_name=pdk)
        #pdk_dict = self.tech_dict[pdk]
        self.tree.insert('PDK', str(self.tree_item_counter), pdk, text=pdk)
        tech_dict = self.graph_controller.graph_control_notebook.tech_dict
        pdk_dict = tech_dict[pdk_name]
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
    def __init__(self, canvas, window, pack_toolbar, expand_callback, graph_settings_callback, top_level_app):
        # Initialize the original NavigationToolbar
        super().__init__(canvas, window, pack_toolbar=pack_toolbar)

        # Create a new frame for the extra row of custom widgets
        # Create your custom widgets and add them to the custom_frame
        self.top_level_app = top_level_app

        self.settings_button = ttk.Button(self, text="Settings", command=graph_settings_callback)
        self.settings_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.expand_button = ttk.Button(self, text="Expand", command=expand_callback)
        self.expand_button.pack(side=tk.LEFT, padx=5, pady=5)


    def on_custom_button_click(self):
        print("Custom button clicked")


class CIDLookupWindow(ttk.Frame):
    def __init__(self, parent, expand_callback, top_level_app):
        super().__init__(parent)
        self.expand_callback = expand_callback
        self.top_level_app = top_level_app
        self.top_level_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.top_level_pane.pack(fill=tk.BOTH, expand=True)
        self.tech_browser = CIDTechBrowser2(self, top_level_app=self.top_level_app)
        self.graphing_window = CIDGraphingWindow(self, expand_callback=expand_callback, lookup_window=self,
                                                        top_level_app=self.top_level_app)
        self.top_level_pane.add(self.tech_browser, weight=1)
        self.top_level_pane.add(self.graphing_window, weight=4)
        self.toolbar = self.graphing_window.toolbar
        self.default_sashpos = 200
        self.after(2500, lambda: self.top_level_pane.sashpos(0, 0))


    def update_graph_from_tech_browser(self, equation_eval=None):
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
            if equation_eval != None:
                print("TODO")
                return 0
            #cid_corner = self.graph_controller.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            param1 = self.graphing_window.x_dropdown.get()
            param2 = self.graphing_window.y_dropdown.get()
            legend_str = pdk + " " + model_name + " " + length + " " + corner
            color = color_list[color_index]
            #cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
            #                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            self.graphing_window.ax.grid(True, which="both")

            color_index += 1
            if color_index >= len(color_list):
                color_index = 0
            #self.graphing_window.canvas.draw()
            self.graphing_window.canvas.draw()

    def add_tech_luts(self, dirname, pdk_name):
        self.tech_browser.add_tech_luts(dirname=dirname, pdk_name=pdk_name)

class CIDGraphingWindow(ttk.Frame):
    def __init__(self, parent, expand_callback, lookup_window, top_level_app):
        super().__init__(parent)
        self.top_level_app = top_level_app
        self.lookup_window = lookup_window
        self.update_button_width = 10
        self.spinbox_width = 5
        self.padx = 2
        self.pady = 2
        self.lookup_val = 0
        self.lookup_label_val = tk.StringVar()
        self.lookup_label_val.set(str(self.lookup_val))
        self.graphing_widget = None
        self.expand_callback = expand_callback
        self.browser_state = "contract"
        self.fig, self.ax = plt.subplots()
        self.t = np.arange(0, 3, .01)
        self.ax.plot(self.t, 2 * np.sin(2 * np.pi * self.t))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.toolbar = CIDNavigationToolbar(self.canvas, self, pack_toolbar=False, expand_callback=self.expand_callback,
                                            graph_settings_callback=self.settings_callback, top_level_app=self.top_level_app)
        self.custom_frame = ttk.Frame(self)
        self.toggle_browser_button = ttk.Button(self.custom_frame, text=">", width=3, command=self.toggle_browser)
        self.toggle_browser_button.pack(side=tk.LEFT, padx=3)

        self.x_label = ttk.Label(self.custom_frame, text="X:")
        self.x_label.pack(side=tk.LEFT, padx=self.padx, pady=self.pady)

        self.x_dropdown = ttk.Combobox(self.custom_frame, width=7)
        self.x_dropdown["values"] = self.top_level_app.lookups
        self.x_dropdown.current(21)
        self.x_dropdown.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)
        self.x_value_lookup = tk.DoubleVar()
        self.x_value_lookup.set(15)
        self.x_spinbox = ttk.Spinbox(self.custom_frame, from_=0, to=100, textvariable=self.x_value_lookup, increment=0.1, width=self.spinbox_width)
        self.x_spinbox.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)
        self.y_label = ttk.Label(self.custom_frame, text="Y:")
        self.y_label.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)

        self.y_dropdown = ttk.Combobox(self.custom_frame, width=7)
        self.y_dropdown["values"] = self.top_level_app.lookups
        self.y_dropdown.current(8)
        self.y_dropdown.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)
        self.y_value_lookup = tk.DoubleVar()
        self.y_value_lookup.set(15)
        self.y_spinbox = ttk.Spinbox(self.custom_frame, from_=0, to=100, textvariable=self.y_value_lookup, increment=0.1, width=self.spinbox_width)
        self.y_spinbox.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)

        self.lookup_label = ttk.Label(self.custom_frame, textvariable=self.lookup_label_val)
        self.lookup_label.pack(side=tk.LEFT, padx=10, pady=self.pady)

        self.update_button = ttk.Button(self.custom_frame, width=self.update_button_width, text="Update",
                                command=self.update_graph)
        self.update_button.pack(side=tk.LEFT, padx=self.padx, pady=self.padx)
        # Pack the custom_frame below the default toolbar
        self.toolbar.update()
        self.custom_frame.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("key_press_event", self.on_key_press)

        self.xlog = False
        self.ylog = False

        self.label_font = None
        self.x_title = ""
        self.y_title = ""
        self.set_3d = False
        self.z_title = ""
        self.colormap_3d = None
        self.set_legend = False



    def settings_callback(self):
        print("TODO")

    def on_key_press(self, event):
        if self.set_3d == True:
            print("TODO")
            z_ticks = np.array([1, 10, 100, 1000, 10000, 100000])
            self.ax.set_zticks(np.log10(z_ticks))
            self.ax.set_zticklabels(z_ticks)
            self.ax.xaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
            self.ax.yaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)
            self.ax.zaxis._axinfo['grid'].update(color='gray', linestyle='--', linewidth=0.5)

            return 0
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

    def get_selected_corners(self):
        models_selected = self.graph_controller.tech_browser.tree.get_checked()
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

    def update_graph(self):
        print("TODO")

    def update_graph_from_tech_browser(self, equation_eval=None):
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
            cid_corner = self.graph_controller.graph_control_notebook.tech_dict[pdk][model_name][length]["corners"][corner]
            if equation_eval != None:
                print("TODO")
                return 0
            #cid_corner = self.graph_controller.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            param1 = self.graph_controller.graph_settings.x_dropdown.get()
            param2 = self.graph_controller.graph_settings.y_dropdown.get()
            legend_str = pdk + " " + model_name + " " + length + " " + corner
            color = color_list[color_index]
            #cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
            #                                 fig1=self.graphing_window.fig, ax1=self.graphing_window.ax, color=color, legend_str=legend_str)
            cid_corner.plot_processes_params(param1=param1, param2=param2, show_plot=False, new_plot=False,
                                 fig1=self.fig, ax1=self.ax, color=color, legend_str=legend_str)
            self.ax.grid(True, which="both")

            color_index += 1
            if color_index >= len(color_list):
                color_index = 0
            #self.graphing_window.canvas.draw()
            self.canvas.draw()

    def toggle_browser(self):
        if self.browser_state == "expand":
            self.browser_state = "contract"
            self.toggle_browser_button.config(text=">")
            self.lookup_window.top_level_pane.sashpos(0, 0)
        else:
            self.browser_state = "expand"
            self.toggle_browser_button.config(text="<")
            self.lookup_window.top_level_pane.sashpos(0, self.lookup_window.default_sashpos)

# Graph Controller is the left pane of the top level application
class CIDGraphController(ttk.PanedWindow):
    def __init__(self, parent, graph_control_notebook, top_level_app, test=False):
        super().__init__(parent, orient=tk.VERTICAL)
        #self.tech_browser = CIDTechBrowser(self, graph_controller=self, theme=theme)
        self.tech_browser = None
        self.top_level_app = top_level_app
        self.graph_control_notebook = graph_control_notebook
        self.graph_settings = CIDOptimizerSettings(self, graph_controller=self, tech_browser=self.tech_browser, top_level_app=self.top_level_app, test=test)
        self.graph_settings.pack(fill=tk.BOTH, expand=True)
        self.graph_settings.rowconfigure(0, weight=1)
        #self.add(self.tech_browser)
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
    def __init__(self, theme, test=False):
        ThemedTk.__init__(self, theme=theme)
        # Create the top-level horizontal paned window
        self.lookups = ('cdb', 'cdd', 'cds', 'cgb', 'cgd', 'cgg', 'cgs', 'css', 'ft', 'gds', 'gm', 'gmb', 'gmidft',
                                     'gmro', 'ic', 'iden', 'ids', 'kcdb', 'kcds', 'kcgd', 'kcgs', 'kgm', 'kgmft', 'n', 'rds',
                                     'ro', 'va', 'vds', 'vdsat', 'vgs', 'vth', 'kgds')

        #self.tech_dict contains all lookup data
        self.tech_dict = {}
        self.top_level_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.top_level_pane.pack(fill=tk.BOTH, expand=True)

        # Left Pane
        #self.left_pane = CIDGraphControlNotebook(self.top_level_pane, top_level_app=self, test=test, width=450)
        self.left_pane = CIDGraphController(self.top_level_pane, graph_control_notebook=None, top_level_app=self, test=False)
        self.graph_controller = self.left_pane
        #self.graph_control_notebook = self.left_pane

        # Center Pane
        self.center_pane = ttk.PanedWindow(self.top_level_pane, orient=tk.VERTICAL)
        self.graph_grid = CIDGraphGrid(self.center_pane, graph_controller=self.graph_controller, top_level_app=self)
        self.center_pane.add(self.graph_grid)

        # Right Pane
        self.right_pane = CIDPythonIDE(self.top_level_pane)
        self.right_pane_width = 300
        self.right_pane.config(width=self.right_pane_width)
        self.ide = self.right_pane

        # Add panes to the top-level paned window
        self.top_level_pane.add(self.left_pane, weight=2)
        self.top_level_pane.add(self.center_pane, weight=3)
        self.top_level_pane.add(self.right_pane, weight=1)

        #self.cid = self.grid_button_widget.

        # After adding the panes, set the sash position for control
        #self.top_level_pane.sashpos(1, 400)  # Position the sash at 400px
        sky130_luts = ROAR_CHARACTERIZATION + "/sky130/LUTs_SKY130"
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/predictive_28/LUTs_1V8_mac", pdk_name="tsmc28_1v8")
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac", pdk_name="sky130")
        #self.left_pane.add_tech_luts(dirname=sky130_luts, pdk_name="sky130")
        self.add_tech_luts(dir=sky130_luts, pdk_name="sky130")
        #self.graph_grid.add_tech_luts(dirname=sky130_luts, pdk_name="sky130")
        # Add a tiny button to mimic being on the handle of the sash
        #self.toggle_button = ttk.Button(self, text="<<", command=self.toggle_right_pane, width=5)
        #self.toggle_button.place(x=405, y=20)  # Place button near the sash handle (adjust as necessary)

        # Track the state of the right pan
        print("Window Initialized")

        print("Window Initialized")
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/predictive_28/LUTs_1V8_mac", pdk_name="tsmc28_1v8")
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac", pdk_name="sky130")
        #self.left_pane.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/sky130/LUTs_SKY130", pdk_name="sky130")
        #self.graph_control_notebook.add_tech_luts(dirname="/work/ala1/gf12lp/characterization_master/LUT_GF12", pdk_name="GF12LP")
        #self.left_pane.add_tech_luts(dirname="/hizz/pro/lteng4448/design/methodics/ala1/ala1_lteng4448/cds_run/ICU_param/characterization_pls_analysis/GF22FDX-PLS", pdk_name="GF22FDXPLUS")
        #self.graph_control_notebook.add_tech_luts(dirname="/hizz/pro/lteng4448/design/methodics/ala1/KARHU_TRUNK/cds_run/characterization/characterization_master/GF22FDX_LUTs", pdk_name="GF22FDXPLUS")
        #self.graph_control_notebook.add_tech_luts(dirname="/home/adair/Documents/CAD/roar/characterization/tsmc28/LUTs_1V8_mac", pdk_name="sky130")

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


    def on_closing(self):
        self.destroy()

    def signal_handler(self, sig, frame):
        self.on_closing()

    def toggle_right_pane(self):
        """Toggle the visibility of the right pane."""
        if self.is_right_pane_collapsed:
            # Expand the right pane
            self.top_level_pane.add(self.right_pane, weight=1)
            self.toggle_right_pane_button.config(text="<<")
            self.is_right_pane_collapsed = False
        else:
            # Collapse the right pane
            self.top_level_pane.forget(self.right_pane)
            self.toggle_right_pane_button.config(text=">>")
            self.is_right_pane_collapsed = True

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

    def add_lookup(self, lookup_name, lookup_values):
        lookup_name = (lookup_name,)
        self.lookups = self.lookups + lookup_name

    def add_tech_luts(self, dir, pdk_name):
        self.tech_dict[pdk_name] = {}
        for filename in os.listdir(dir):
            f = os.path.join(dir, filename)
            if os.path.isdir(f):
                model_name = filename
                self.create_devices_from_model_dir(pdk_name=pdk_name, model_name=model_name, model_dir=f)
        self.graph_grid.add_tech_luts(dirname=dir, pdk_name=pdk_name)
        return (self.tech_dict)


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


class CIDGraphGrid(ttk.Frame):
    def __init__(self, master, graph_controller, top_level_app, **kwargs):
        super().__init__(master, **kwargs)

        # Initialize the grid
        self.graphing_windows = []
        self.graph_positions = []
        self.lookup_windows = []
        self.graph_controller = graph_controller
        self.top_level_app = top_level_app

        graph_counter = 0
        for i in range(2):
            self.grid_rowconfigure(i, weight=1)
            for j in range(2):
                self.grid_columnconfigure(j, weight=1)
                #graph = CIDGraphingWindow(self, expand_callback=lambda x=i, y=j: self.toggle_expand(x, y),
                #                          graph_controller=self.graph_controllers[graph_counter], top_level_app=self.top_level_app)
                graph = CIDLookupWindow(self, expand_callback=lambda x=i, y=j: self.toggle_expand(x, y), top_level_app=self.top_level_app)
                self.lookup_windows.append(graph)
                #graph_controller.set_graphing_widget(graph)
                graph.grid(row=i,column=j,sticky="nsew")
                self.graphing_windows.append(graph)
                self.graph_positions.append((i, j))
                graph.top_level_pane.sashpos(0, 0)

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

    def add_tech_luts(self, dirname, pdk_name):
        #self.add_tech_from_dir(dir=dirname, pdk_name=pdk_name)
        for lookup_window in self.lookup_windows:
            lookup_window.add_tech_luts(dirname=dirname, pdk_name=pdk_name)


# Graft Control Notebook is the top left widget of the top level application
class CIDGraphControlNotebook(ttk.Notebook):
    def __init__(self, master=None, test=False, top_level_app=None, **kw):
        super().__init__(master, **kw)
        self.top_level_app = top_level_app
        self.master = master
        self.graph_controllers = []
        self.tech_dict = {}
        self.create_widgets(test)
        self.lookups = None

    def create_widgets(self, test):
        tab_titles = ["Upper Left", "Upper Right", "Lower Left", "Lower Right"]
        tab_counter = 0
        for i in range(0, 4):
            tab = ttk.Frame(self)
            self.add(tab, text=tab_titles[i])
            graph_controller = CIDGraphController(tab, graph_control_notebook=self, top_level_app=self.top_level_app, test=False)
            graph_controller.pack(expand=True, fill="both")
            self.graph_controllers.append(graph_controller)
            tab_counter = tab_counter + 1
        self.bind("<<NotebookTabChanged>>", self.tab_changed)

    def add_tech_luts(self, dirname, pdk_name):
        self.add_tech_from_dir(dir=dirname, pdk_name=pdk_name)
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

    def set_lookups(self, lookups):
        self.lookups = lookups


    def tab_changed(self, event):
        current_tab = self.index("current")
        #print("Tab Changed to:", current_tab)

class CIDCornerSelector(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Device and Corner Selection")


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

def on_file_new():
    print("New File")

def on_solver_run():
    print("Run Solver")

def on_export_file():
    print("Export File")

def on_help_about():
    print("About Help")


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
    elif test_app == 5:
        root = tk.Tk()
        root.title("CIDPaintWidget Demo")
        #paint_widget = CIDExpressionWidget(root)
        paint_widget = CIDPaintWidget(root)
        paint_widget.pack(fill=tk.BOTH, expand=True)

        root.mainloop()
    else:
        theme = "arc"
        app = CIDApp(theme, test=False)
        app.title("ROAR")
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        signal.signal(signal.SIGINT, app.signal_handler)
        signal.signal(signal.SIGTERM, app.signal_handler)
        signal.signal(signal.SIGQUIT, app.signal_handler)

        # Load the icon image using PIL and set it to the Toplevel window
        icon_path = ROAR_HOME + "/images/png/ROAR_ICON.png"
        icon_image = Image.open(icon_path)
        # Resize the icon if necessary (optional)
        icon_image_resized = icon_image.resize((32, 32))  # Optional: Resize to 32x32 pixels
        icon_photo = ImageTk.PhotoImage(icon_image_resized)

        # Set the icon for the Toplevel window
        app.iconphoto(True, icon_photo)

        style = ttk.Style()
        style.theme_use(theme)

        # Get the foreground color from the current theme (TButton or TLabel can be used)
        #fg_color = style.lookup("TButton", "background")
        # Set the foreground color as the background for all widget types
        #style.configure("TFrame", background=fg_color)
        #style.configure("TLabel", background=fg_color)
        #style.configure("TButton", background=fg_color)
        #style.configure("TEntry", background=fg_color)
        #style.configure("TCombobox", background=fg_color)
        #app.configure(bg=fg_color)
        menu_bar = tk.Menu(app)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=on_file_new)
        file_menu.add_command(label="Open", command=lambda: print("Open File"))
        file_menu.add_command(label="Save", command=lambda: print("Save File"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=app.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Solver Menu
        solver_menu = tk.Menu(menu_bar, tearoff=0)
        solver_menu.add_command(label="Run Solver", command=on_solver_run)
        solver_menu.add_command(label="Stop Solver", command=lambda: print("Stop Solver"))
        menu_bar.add_cascade(label="Solver", menu=solver_menu)

        # Window Menu
        window_menu = tk.Menu(menu_bar, tearoff=0)
        window_menu.add_command(label="Minimize", command=lambda: print("Minimize Window"))
        window_menu.add_command(label="Maximize", command=lambda: print("Maximize Window"))
        menu_bar.add_cascade(label="Window", menu=window_menu)

        # Export Menu
        export_menu = tk.Menu(menu_bar, tearoff=0)
        export_menu.add_command(label="Export to PDF", command=on_export_file)
        export_menu.add_command(label="Export to Image", command=lambda: print("Export to Image"))
        menu_bar.add_cascade(label="Export", menu=export_menu)

        # Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=on_help_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        app.config(menu=menu_bar)
        app.left_pane.update()
        app.left_pane.update_idletasks()
        # Configure the style to use the theme
        #style.theme_use(theme)  # You can choose different themes here
        #ttk.Style().theme_use('clam')
        app.mainloop()
