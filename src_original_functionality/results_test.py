import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog


# Function to add a new tab with a name entered by the user
def add_new_tab():
    # Ask the user for the design name
    design_name = simpledialog.askstring("Input", "Enter Design Name")

    # If the user cancels or enters nothing, do not create a new tab
    if not design_name:
        return

    # Create a new frame for the new tab
    new_tab = tk.Frame(notebook)

    # Add some content to the new tab (e.g., a label)
    label = tk.Label(new_tab, text=f"This is {design_name}", background="lightyellow")
    label.pack(padx=10, pady=10)

    # Add the new tab to the notebook, just before the "+" tab
    notebook.insert(notebook.index("end") - 1, new_tab, text=design_name)

    # Switch to the new tab after adding
    notebook.select(notebook.index("end") - 2)


# Function to handle tab changes and check if the "+" tab is selected
def on_tab_change(event):
    if notebook.index(notebook.select()) == notebook.index("end") - 1:
        add_new_tab()


# Create the main application window
root = tk.Tk()
root.title("Notebook with + Tab and Design Name Input")

# Create a Notebook widget
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=1)

# Create a few initial tabs
tab1 = tk.Frame(notebook)
tab2 = tk.Frame(notebook)
notebook.add(tab1, text="Tab 1")
notebook.add(tab2, text="Tab 2")

# Create a label in each tab
label1 = tk.Label(tab1, text="This is Tab 1", background="lightblue")
label1.pack(padx=10, pady=10)

label2 = tk.Label(tab2, text="This is Tab 2", background="lightgreen")
label2.pack(padx=10, pady=10)

# Add the "+" tab
plus_tab = tk.Frame(notebook)
notebook.add(plus_tab, text="+")

# Bind the event that checks for tab changes
notebook.bind("<<NotebookTabChanged>>", on_tab_change)

root.mainloop()