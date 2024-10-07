import tkinter as tk
from tkinter import ttk

class CIDCheckBoxListPane(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.paned_window = ttk.PanedWindow(self, orient="horizontal")
        self.paned_window.pack(expand=True, fill="both", padx=10, pady=10)

        entries1 = ["PDK1", "PDK2", "PDK3", "PDK4", "PDK5", "PDK6", "PDK7", "PDK8", "PDK9", "PDK10", "PDK11", "PDK12"]
        entries2 = ["Device1", "Device2", "Device3", "Device4", "Device5", "Device6", "Device7", "Device8", "Device9", "Device10"]
        entries3 = ["Short", "Medium", "Long", "Extra Long", "Super Long", "Ultra Long", "Mega Long"]
        entries4 = ["Corner1", "Corner2", "Corner3", "Corner4", "Corner5", "Corner6"]

        checkbox_list1 = self.create_checkbox_list("PDK", entries1)
        self.paned_window.add(checkbox_list1)

        checkbox_list2 = self.create_checkbox_list("Device", entries2)
        self.paned_window.add(checkbox_list2)

        checkbox_list3 = self.create_checkbox_list("Length", entries3)
        self.paned_window.add(checkbox_list3)

        checkbox_list4 = self.create_checkbox_list("Corner", entries4)
        self.paned_window.add(checkbox_list4)

    def create_checkbox_list(self, label_text, entries):
        checkbox_list = CIDCheckBoxList(self.paned_window, label_text, entries)
        return checkbox_list

class CIDCheckBoxList(tk.Frame):
    def __init__(self, master, label_text, entries, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.entries = entries

        self.label = ttk.Label(self, text=label_text)
        self.label.pack(fill="x", pady=5)

        self.checkboxes_frame = tk.Frame(self)
        self.checkboxes_frame.pack(fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.checkboxes_frame)
        self.scrollbar.pack(side="right", fill="y")

        self.checkboxes_canvas = tk.Canvas(self.checkboxes_frame, yscrollcommand=self.scrollbar.set)
        self.checkboxes_canvas.pack(side="left", fill="both", expand=True)

        self.checkboxes_inner_frame = tk.Frame(self.checkboxes_canvas)
        self.checkboxes_canvas.create_window((0, 0), window=self.checkboxes_inner_frame, anchor="nw")

        self.scrollbar.config(command=self.checkboxes_canvas.yview)

        self.checkboxes_inner_frame.bind("<Configure>", self.on_frame_configure)

        self.checkboxes = []
        for i, entry in enumerate(entries):
            var = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(self.checkboxes_inner_frame, text=entry, variable=var)
            checkbox.grid(row=i, column=0, sticky="w")
            self.checkboxes.append(var)

        # All button
        self.all_button = ttk.Button(self, text="All", command=self.select_all)
        self.none_button = ttk.Button(self, text="None", command=self.deselect_all)
        
        # Pack buttons to the bottom
        self.all_button.pack(side="left", padx=5)
        self.none_button.pack(side="left", padx=5)

    def on_frame_configure(self, event):
        self.checkboxes_canvas.configure(scrollregion=self.checkboxes_canvas.bbox("all"))

    def select_all(self):
        for checkbox in self.checkboxes:
            checkbox.set(True)

    def deselect_all(self):
        for checkbox in self.checkboxes:
            checkbox.set(False)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("CIDCheckBoxListPane Demo")

    checkbox_list_pane = CIDCheckBoxListPane(root)
    checkbox_list_pane.pack(expand=True, fill="both")

    root.mainloop()
