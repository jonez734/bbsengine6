import argparse

import tkinter as tk
from tkinter import ttk

import ttyio5 as ttyio
import bbsengine5 as bbsengine


class App(tk.Tk):
    def __init__(self, args):
        super().__init__()

        self.args = args

#        self.geometry('300x110')
#        self.resizable(0, 0)
        self.title('Login')
        # UI options
        paddings = {'padx': 5, 'pady': 5}
        entry_font = {'font': ('Helvetica', 11)}

        # configure the grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)

        self.name = tk.StringVar()
        self.password = tk.StringVar()

        # username
        self.name_label = ttk.Label(self, text="Name:")
        self.name_label.grid(column=0, row=0, sticky=tk.W, **paddings)

        self.name_entry = ttk.Entry(self, textvariable=self.name, **entry_font)
        self.name_entry.grid(column=1, row=0, sticky=tk.E, **paddings)

        # password
        self.password_label = ttk.Label(self, text="Password:")
        self.password_label.grid(column=0, row=1, sticky=tk.W, **paddings)

        self.password_entry = ttk.Entry(self, textvariable=self.password, show="*", **entry_font)
        self.password_entry.grid(column=1, row=1, sticky=tk.E, **paddings)

        # login button
        self.login_button = ttk.Button(self, text="Login", command=self.check)
        self.login_button.grid(column=1, row=3, sticky=tk.E, **paddings)

        # configure style
        self.style = ttk.Style(self)
        self.style.configure('TLabel', font=('Helvetica', 11))
        self.style.configure('TButton', font=('Helvetica', 11))
        self.bind('<Escape>', lambda e: self.close(e))

    def check(self):
        name = self.name.get()
        password = self.password.get()
        memberid = bbsengine.getmemberidfromname(self.args, name)
        ttyio.echo(f"name={name!r} password={password!r} memberid={memberid!r}", level="debug")
        if memberid is False:
            ttyio.echo("you do not exist! go away!")
            return

        if bbsengine.checkpassword(args, password, memberid) is True:
            ttyio.echo("password is correct")
            self.destroy()
        else:
            ttyio.echo("password is wrong")
            self.password_entry.delete(0, tk.END)

    def close(self, e):
       self.destroy()

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("tklogin")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

#    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":15433, "databasepassword":None} # port=5432
    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None} # port=5432
    bbsengine.buildargdatabasegroup(parser, defaults)

    return parser

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    app = App(args)
    app.mainloop()
