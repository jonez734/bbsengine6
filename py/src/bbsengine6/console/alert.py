def alerts(args):
    def elle():
        sql = "select * from alert where membermoniker=%s"
        dat = (member.moniker,)

    done = False
    while not done:
        util.heading("alerts")
        io.echo("{var:optioncolor}[L]{var:labelcolor} List")
        io.echo("{var:optioncolor}[S]{var:labelcolor} Send")
        io.echo("{var:optioncolor}[R]{var:labelcolor} Read")
        io.echo("{var:optioncolor}[X]{var:labelcolor} Exit")
        io.echo()
        ch = io.inputchar("{var:promptcolor}alert [LSRX]: {var:inputcolor}", "LSRXQ")
        if ch == "L":
            io.echo("List")
            elle()
        elif ch == "S":
            ess()
        elif ch == "R":
            arr()
        elif ch == "X" or ch == "Q":
            done = True
        else:
            io.echo("{bell}", end="", flush=True)
