import tkinter as tk
from tkinter import ttk


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("400x200")
        self.title("Main Window")

        # Create a Label in the main window
        self.label = ttk.Label(self, text="Initial Text", font=('Arial', 14))
        self.label.pack(pady=20)

        # Button to move the label to a new window for editing
        edit_button = ttk.Button(self, text="Edit Label", command=self.open_edit_window)
        edit_button.pack(pady=10)

    def open_edit_window(self):
        """Open a new window to edit the label widget."""
        # Create a new window and pass the Label widget to the EditWindow
        self.edit_window = EditWindow(self, self.label)

    def return_label(self, updated_label):
        """Repack the updated label back into the main window."""
        self.label = updated_label
        self.label.pack(pady=20)


class EditWindow(tk.Toplevel):
    def __init__(self, parent, label_widget):
        super().__init__(parent)
        self.title("Edit Label")
        self.geometry("300x150")
        self.parent = parent

        # Store the label widget from the main window
        self.label_widget = label_widget

        # Remove the label from the main window and pack it into this window
        self.label_widget.pack_forget()  # Remove from the parent window
        self.label_widget.pack(pady=20)  # Repack into the new window

        # Entry widget to modify the label text
        self.entry = ttk.Entry(self, font=('Arial', 14))
        self.entry.insert(0, self.label_widget['text'])
        self.entry.pack(pady=10)

        # Button to save the changes and close the window
        save_button = ttk.Button(self, text="Save and Close", command=self.on_save)
        save_button.pack(pady=10)

        # Bind the window close event to handle returning the label
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_save(self):
        """Save the edited text to the label and return it to the parent window."""
        new_text = self.entry.get()
        self.label_widget.config(text=new_text)  # Update the label's text

        # Return the label widget to the parent window
        self.parent.return_label(self.label_widget)
        self.destroy()  # Close this edit window

    def on_close(self):
        """Handle the window close event to return the label widget."""
        self.on_save()  # Save and return the label when closing


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
