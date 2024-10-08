from tkinter import *
import ctypes
import re
import os
from tkinter import ttk
import sv_ttk

# Increas Dots Per inch so it looks sharper
# Breaking on linux
#ctypes.windll.shcore.SetProcessDpiAwareness(True)

# Setup Tkinter
#root = Tk()
#root.geometry('500x500')


class CIDPythonEditor(ttk.PanedWindow):
    def __init__(self, parent):
        super().__init__(parent)

        self.previousText = ''

        # Define colors for the variouse types of tokens
        self.normal = self.rgb((234, 234, 234))
        self.keywords = self.rgb((234, 95, 95))
        self.comments = self.rgb((95, 234, 165))
        self.string = self.rgb((234, 162, 95))
        self.function = self.rgb((95, 211, 234))
        self.background = self.rgb((42, 42, 42))
        self.font = 'courier 12'

        # Define a list of Regex Pattern that should be colored in a certain way
        self.repl = [
            ['(^| )(False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)($| )', self.keywords],
            ['".*?"', self.string],
            ['\'.*?\'', self.string],
            ['#.*?$', self.comments],
        ]

        self.editArea = Text(
            self,
            background=self.background,
            foreground=self.normal,
            insertbackground=self.normal,
            relief=FLAT,
            borderwidth=30,
            font=self.font
        )

        # Place the Edit Area with the grid method
        self.editArea.grid()

        ## Place the Edit Area with the pack method
        #self.editArea.pack(
        #    fill=BOTH,
        #    expand=1
        #)
        # Insert some Standard Text into the Edit Area
        self.editArea.insert('1.0',
"""
import cid
import string

# Setting up the Argument Parser
corner_example = CIDCorner(name=test_corner_tt,
    lut_dir='/path/to/lookup/tables/directory.'
)
av = 100
bw = 50e6
cload = 250e-15
kgm_opt = corner_example.magic_equation(gain=av, bw=bw, cload=cload, epsilon=10)
print("Kgm Optimal:" + str(kgm_opt)) 
""")

        # Bind the KeyRelase to the Changes Function
        self.editArea.bind('<KeyRelease>', self.changes)

        # Bind Control + R to the exec function
        parent.bind('<Control-r>', self.execute)

        self.changes()

    # Execute the Programm
    def execute(self, event=None):

        # Write the Content to the Temporary File
        with open('run.py', 'w', encoding='utf-8') as f:
            f.write(self.editArea.get('1.0', END))

        # Start the File in a new CMD Window
        os.system('start cmd /K "python run.py"')

    # Register Changes made to the Editor Content
    def changes(self, event=None):
        #global previousText

        # If actually no changes have been made stop / return the function
        if self.editArea.get('1.0', END) == self.previousText:
            return

        # Remove all tags so they can be redrawn
        for tag in self.editArea.tag_names():
            self.editArea.tag_remove(tag, "1.0", "end")

        # Add tags where the search_re function found the pattern
        i = 0
        for pattern, color in self.repl:
            for start, end in self.search_re(pattern, self.editArea.get('1.0', END)):
                self.editArea.tag_add(f'{i}', start, end)
                self.editArea.tag_config(f'{i}', foreground=color)

                i = i + 1

        self.previousText = self.editArea.get('1.0', END)

    def search_re(self, pattern, text, groupid=0):
        matches = []

        text = text.splitlines()
        for i, line in enumerate(text):
            for match in re.finditer(pattern, line):

                matches.append(
                    (f"{i + 1}.{match.start()}", f"{i + 1}.{match.end()}")
                )

        return matches


    def rgb(self, rgb):
        return "#%02x%02x%02x" % rgb

