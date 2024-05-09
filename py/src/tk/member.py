import argparse

import tkinter as tk
from tkinter import ttk

import ttyio5 as ttyio
import bbsengine5 as bbsengine

class App(tk.Tk):
    def __init__(self, args):
        super().__init__()

        self.args = args
        self.sysop = False # bbsengine.checksysop(args)
        
        self.vars = {}

        self.title('Edit Member')
        # UI options
        paddings = {'padx': 10, 'pady': 10}

        # configure style
        self.style = ttk.Style(self)
        self.style.configure("TLabel",  font=("TkFixedFont", 11))
        self.style.configure("TButton", font=("TkFixedFont", 11)) #Helvetica", 11))
        self.style.configure("TEntry",  font=("TkFixedFont", 11))

        # configure the grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)

        # self.datecreated = tk.StringVar()
        
        ttyio.echo(f"self.args={self.args!r}", level="debug")
        self.dbh = bbsengine.databaseconnect(self.args)

        self.memberid = bbsengine.getcurrentmemberid(args)
        self.member = bbsengine.getmemberbyid(self.dbh, self.memberid)

        row = 0

        # name
        self.name = tk.StringVar()

        self.name_label = ttk.Label(self, text="name")
        self.name_label.grid(column=0, row=row, sticky=tk.W, **paddings)

        self.name_entry = ttk.Entry(self, textvariable=self.name)
        self.name_entry.grid(column=1, row=row, sticky=tk.E, **paddings)

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.member["name"])
        
        if self.sysop is False:
            self.name_entry.config(state="disabled")

        row += 1

        # email
        self.email = tk.StringVar()

        self.email_label = ttk.Label(self, text="email")
        self.email_label.grid(column=0, row=row, sticky=tk.W, **paddings)
        
        self.email_entry = ttk.Entry(self, textvariable=self.email)
        self.email_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        self.email_entry.delete(0, tk.END)
        self.email_entry.insert(0, self.member["email"])
        
        row += 1

        # date created
        
        self.datecreated = tk.StringVar()

        self.datecreated_label = ttk.Label(self, text="date created")
        self.datecreated_label.grid(column=0, row=row, sticky=tk.W, **paddings)
        
        self.datecreated_entry = ttk.Entry(self, textvariable=self.datecreated)
        self.datecreated_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        self.datecreated_entry.delete(0, tk.END)
        self.datecreated_entry.insert(0, self.member["datecreated"])

        row += 1
        
        self.member["flags"] = bbsengine.getflags(self.args, self.memberid)

        for v in self.member["flags"].values():
            v["var"] = tk.BooleanVar()

        ttyio.echo(f"flags={self.member['flags']!r}", level="debug")
        flags_frame = tk.LabelFrame(self, borderwidth=2, relief=tk.GROOVE, text="Flags")
        flags_frame.grid(column=0, row=row, columnspan=2, sticky=tk.W+tk.E, **paddings)
        
        self.flagvars = {}
        for f, v in self.member["flags"].items():
            ttyio.echo(f"f={f!r} v={v!r}", level="debug") #  v.value={v['value']!r} v.description={v['description']!r}", level="debug")
            self.flagvars[f] = tk.BooleanVar()
            self.flagvars[f].set(v["value"])
            
            flag_checkbutton = tk.Checkbutton(flags_frame, text=v["description"], variable=self.member["flags"][f]["var"], onvalue=True, offvalue=False)
            flag_checkbutton.pack(anchor=tk.W)

            if v["value"] is True:
                self.member["flags"][f]["var"].set(True)
            else:
                self.member["flags"][f]["var"].set(False)

            if f == "AUTHENTICATED":
                flag_checkbutton.configure(state=tk.DISABLED)

        row += 1

        # notify count
        self.notifycount = tk.IntVar()

        self.notifycount_label = ttk.Label(self, text="notify count:")
        self.notifycount_label.grid(column=0, row=row, sticky=tk.W, **paddings)

        self.notifycount_entry = ttk.Entry(self, textvariable=self.notifycount)
        self.notifycount_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        if self.sysop is False:
            self.notifycount_entry.config(state="disabled")

        row += 1
        self.credits = tk.IntVar()
        
        self.credits_label = ttk.Label(self, text="credits")
        self.credits_label.grid(column=0, row=row, sticky=tk.E, **paddings)
        
        self.credits_entry = ttk.Entry(self, textvariable=self.notifycount)
        self.credits_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        if self.sysop is False:
            self.credits_entry.config(state="disabled")

        row += 1

        self.loginid = tk.StringVar()
        self.loginid_label = ttk.Label(self, text="loginid")
        self.loginid_label.grid(column=0, row=row, sticky=tk.E, **paddings)

        self.loginid_entry = ttk.Entry(self, textvariable=self.loginid)
        self.loginid_entry.grid(column=1, row=row, sticky=tk.E, **paddings)
        if self.sysop is False:
            self.loginid_entry.config(state="disabled")

        row += 1

        self.uivars = {
            "tkinter": {"var":tk.BooleanVar()},
            "ansi":    {"var":tk.BooleanVar()},
            "web":     {"var":tk.BooleanVar()}
        }
        ui_frame = tk.LabelFrame(self, borderwidth=2, relief=tk.GROOVE, text="UI")
        ui_frame.grid(column=0, row=row, columnspan=2, sticky=tk.W+tk.E, **paddings)
        for n, v in self.uivars.items():
            ui_checkbutton = tk.Checkbutton(ui_frame, text=n, variable=self.uivars[n]["var"], onvalue=True, offvalue=False)
            ui_checkbutton.pack(anchor=tk.W)

        row += 1

        # update button
        self.change_button = ttk.Button(self, text="update member", command=self.update)
        self.change_button.grid(column=1, row=row, sticky=tk.E, **paddings)
        
        if self.sysop is True:
            self.name_entry.focus_set()
        else:
            self.email_entry.focus_set()

        self.bind('<Escape>', lambda e: self.quit())

    def update(self):
        name = self.name.get()
        if self.memberid is None:
            ttyio.echo("you do not exist! go away!")
            return
        for k, v in self.vars.items():
            ttyio.echo(f"{k!r}={v.get()!r}", level="debug")
#        ttyio.echo(f"vars={vars!r}", level="debug")

        ttyio.echo("update button clicked", level="debug")
        ui = []
        for k, v in self.uivars.items():
#            ttyio.echo(f"{k}={v['var'].get()}", level="debug")
            if v["var"].get() is True:
                ui.append(k)
        self.member["ui"] = " ".join(ui)

        for v in self.member["flags"].values():
            ttyio.echo(f"self.member.update.100: v.var.get(): {v['var'].get()}", level="debug")
            if v["var"].get() is True:
                v["value"] = True
            else:
                v["value"] = False
            ttyio.echo(f"self.member.flags.100: v={v!r}", level="debug")
        ttyio.echo(f"self.member.flags={self.member['flags']!r}", level="debug")
        ttyio.echo(f"self.dbh={self.dbh!r}", level="debug")
        ttyio.echo(f"self.member={self.member!r} type={type(self.member)}", level="debug")
        bbsengine.updatemember(self.args, self.member, self.memberid)
        bbsengine.setmemberflags(self.args, self.member["flags"], self.memberid)
        self.dbh.commit()
        
    def close(self, e):
        # ttyio.echo(f"tkmember.close.100: {e!r}", level="debug")
        self.destroy()

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("member")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

#    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":15433, "databasepassword":None} # port=5432
    defaults = {"databasename": "zoidweb5", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None} # port=5432
    bbsengine.buildargdatabasegroup(parser)

    return parser

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    ttyio.echo(f"__main__.100: args={args!r}", level="debug")
    app = App(args)
    app.mainloop()
