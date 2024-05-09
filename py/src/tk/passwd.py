import argparse

import tkinter as tk
from tkinter import ttk

import ttyio5 as ttyio
import bbsengine5 as bbsengine


class App(tk.Tk):
    def __init__(self, args):
        super().__init__()

        self.args = args

        self.title('Change Password')
        # UI options
        paddings = {'padx': 5, 'pady': 5}
        entry_font = {'font': ('monospace', 11)}

        # configure the grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)

        self.username = tk.StringVar()
        self.new_password = tk.StringVar()
        self.old_password = tk.StringVar()
        self.repeat_password = tk.StringVar()

        # username
        self.username_label = ttk.Label(self, text="Username:")
        self.username_label.grid(column=0, row=0, sticky=tk.W, **paddings)

        self.username_entry = ttk.Entry(self, textvariable=self.username, **entry_font)
        self.username_entry.grid(column=1, row=0, sticky=tk.E, **paddings)
        self.username_entry.delete(0, tk.END)
        self.username_entry.insert(0, bbsengine.getmembername(args))

        self.sysop = False # bbsengine.checksysop(self.args)

        row = 1
        # old_password
        if self.sysop is False:
            self.old_password_label = ttk.Label(self, text="Old Password:")
            self.old_password_label.grid(column=0, row=row, sticky=tk.W, **paddings)

            self.old_password_entry = ttk.Entry(self, textvariable=self.old_password, show="*", **entry_font)
            self.old_password_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
            
            self.username_entry.config(state="disabled")

            row += 1

        self.new_password_label = ttk.Label(self, text="New Password:")
        self.new_password_label.grid(column=0, row=row, sticky=tk.W, **paddings)

        self.new_password_entry = ttk.Entry(self, textvariable=self.new_password, show="*", **entry_font)
        self.new_password_entry.grid(column=1, row=row, sticky=tk.E, **paddings)

        row += 1
        self.repeat_password_label = ttk.Label(self, text="Repeat Password:")
        self.repeat_password_label.grid(column=0, row=row, sticky=tk.W, **paddings)

        self.repeat_password_entry = ttk.Entry(self, textvariable=self.repeat_password, show="*", **entry_font)
        self.repeat_password_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        
        row += 1

        # change button
        self.change_button = ttk.Button(self, text="change password", command=self.change)
        self.change_button.grid(column=1, row=row, sticky=tk.E, **paddings)

        # configure style
        self.style = ttk.Style(self)
        self.style.configure('TLabel', font=('Helvetica', 11))
        self.style.configure('TButton', font=('Helvetica', 11))

    def change(self):
        username = self.username.get()
        new_password = self.new_password.get()
        old_password = self.old_password.get()
        repeat_password = self.repeat_password.get()

        self.repeat_password_entry.delete(0, tk.END)
        self.new_password_entry.delete(0, tk.END)
        if self.sysop is False:
            self.old_password_entry.delete(0, tk.END)
        self.repeat_password_entry.delete(0, tk.END)
        
        if self.sysop is False:
            if bbsengine.checkpassword(args, old_password) is False:
                ttyio.echo("password mismatch (oldpassword)", level="error")
                return

        if new_password != repeat_password:
            ttyio.echo("enter your new password twice", level="error") # dialog box?
            return

        ttyio.echo(f"username={username!r}", level="debug")
        ttyio.echo(f"new_password={new_password!r}", level="debug")
        memberid = bbsengine.getmemberidfromname(self.args, username)
        if memberid is False:
            ttyio.echo("you do not exist! go away!", level="error")
            return

        if self.new_password == "" and self.repeat_password == "":
            ttyio.echo("empty passwords are not allowed", level="error")
            return

        bbsengine.setpassword(args, new_password)

        dbh = bbsengine.databaseconnect(args)
        dbh.commit()
#        if bbsengine.checkpassword(args, username, memberid) is True:
#            ttyio.echo("password is correct")
#        else:
#            ttyio.echo("password is wrong")
#        ttyio.echo(f"memberid={memberid!r}", level="debug")

    def close(self, e):
       self.destroy()

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("tkpasswd")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":15433, "databasepassword":None} # port=5432
#    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None} # port=5432
    bbsengine.buildargdatabasegroup(parser, defaults)

    return parser

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    app = App(args)
    app.bind('<Escape>', lambda e: app.close(e))
    app.mainloop()
