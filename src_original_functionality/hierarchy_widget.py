import tkinter as tk

class HierarchyWidget(tk.Frame):
    def __init__(self, master, hierarchy_data, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.pdk_selection = tk.OptionMenu(self, tk.StringVar)

        """
        self.hierarchy_data = hierarchy_data
        self.selected_options = {}
        
        self.dropdowns = []
        for i, level_data in enumerate(self.hierarchy_data):
            label = tk.Label(self, text=f"Level {i+1}:")
            label.grid(row=i, column=0, sticky="w")
            
            dropdown = tk.OptionMenu(self, tk.StringVar(), *level_data["options"], command=self.update_selection)
            dropdown.grid(row=i, column=1, sticky="w")
            self.dropdowns.append(dropdown)
            
            for option in level_data["options"]:
                self.selected_options[option] = tk.BooleanVar()
                checkbox = tk.Checkbutton(self, text=option, variable=self.selected_options[option])
                checkbox.grid(row=i, column=2, sticky="w")
        """


    def update_selection(self, selected_option):
        # Update selected option for the current dropdown
        level = self.dropdowns.index(self.focus_get())
        self.selected_options[selected_option].set(True)
        
        # Disable options in subsequent dropdowns based on current selection
        for i in range(level + 1, len(self.dropdowns)):
            dropdown = self.dropdowns[i]
            dropdown["menu"].delete(0, "end")  # Clear existing options
            
            # Populate options for the dropdown based on selected options
            available_options = [option for option in self.hierarchy_data[i]["options"]
                                 if all(self.selected_options[parent_option].get() for parent_option in self.hierarchy_data[i]["parents"][option])]
            for option in available_options:
                dropdown["menu"].add_command(label=option, command=tk._setit(tk.StringVar(), option))
                
            # Reset selection for the current dropdown
            dropdown["text"] = "Select Option"
            dropdown.var.set("")
            dropdown.var.trace("w", self.update_selection)
            
if __name__ == "__main__":
    # Example hierarchical data
    hierarchy_data = [
        {
            "options": ["A", "B", "C"],
            "parents": {"A": [], "B": [], "C": []}
        },
        {
            "options": ["1", "2", "3"],
            "parents": {"1": ["A"], "2": ["A"], "3": ["B"]}
        },
        {
            "options": ["X", "Y", "Z"],
            "parents": {"X": ["1"], "Y": ["1"], "Z": ["2"]}
        }
    ]

    root = tk.Tk()
    root.title("Hierarchy Widget")

    hierarchy_widget = HierarchyWidget(root, hierarchy_data)
    hierarchy_widget.pack(padx=10, pady=10)

    root.mainloop()

