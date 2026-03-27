from bbsengine6 import io, util
from bbsengine6.inputdate import inputdate as _inputdate


def email(args, **kwargs):
    def _edit(args, **kwargs):
        if "prompt" in kwargs:
            prompt = kwargs["prompt"]
        else:
            prompt = "email._edit"

        attributes = {}
        if "attributes" in kwargs:
            attributes = kwargs["attributes"]
        done = False
        while not done:
            if "address" in attributes:
                address = attributes["address"]
                if address is not None:
                    io.echo("[A]ddress: %s" % (address))
            else:
                io.echo("[A]ddress")
            io.echo("[P]assword")
            if "status" in attributes:
                status = attributes["status"]
                io.echo("[S]tatus: %s" % (status), end="")
                if status == "suspend" and "suspenduntil" in attributes:
                    suspenduntil = attributes["suspenduntil"]
                    io.echo(" until: %s" % (util.datestamp(suspenduntil)))
                else:
                    io.echo()
            else:
                io.echo("[S]tatus")
            io.echo("[H]ost")
            io.echo("{f6}[Q]uit")
            ch = io.inputchar("%s [AEDSQ]: " % (prompt), "ASMHQ", "Q")
            if ch == "Q":
                io.echo("quit")
                done = True
                break
            elif ch == "P":
                p = util.inputpassword("password: ", mask="X")
                attributes["password"] = p
            elif ch == "A":
                if "address" in attributes:
                    address = attributes["address"]
                else:
                    address = None
                attributes["address"] = io.inputstring(
                    "address: ", address, noneok=True
                )
            elif ch == "H":
                if "host" in attributes:
                    default = attributes["host"]
                else:
                    default = "merlin.zoidtechnologies.com"
                host = io.inputstring("host: ", default)
                attributes["host"] = host

            elif ch == "S":
                ch = io.inputchar("Status [S]uspend [A]ctive: ", "SA", noneok=True)
                if ch == "S":
                    suspenduntil = _inputdate("Suspend until: ")
                    attributes["suspenduntil"] = suspenduntil
                    attributes["status"] = "suspend"
                elif ch == "A":
                    io.echo("Active")
                    attributes["status"] = "active"
                    if "suspenduntil" in attributes:
                        del attributes["suspenduntil"]

        io.echo("_editemail.100: attributes=%r" % (attributes), interpret=False)
        return

    def delete():
        pass

    def edit():
        pass

    def add():
        newattributes = _edit(args, attributes={}, prompt="email.add")
        io.echo("email.add.100: newattributes=%r" % (newattributes), interpret=False)
        return

    def summary():
        pass
