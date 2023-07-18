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
          ttyio.echo("[A]ddress: %s" % (address))
      else:
        ttyio.echo("[A]ddress")
      ttyio.echo("[P]assword")
      if "status" in attributes:
        status = attributes["status"]
        ttyio.echo("[S]tatus: %s" % (status), end="")
        if status == "suspend" and "suspenduntil" in attributes:
          suspenduntil = attributes["suspenduntil"]
          ttyio.echo(" until: %s" % (bbsengine.datestamp(suspenduntil)))
        else:
          ttyio.echo()
      else:
          ttyio.echo("[S]tatus")
      ttyio.echo("[H]ost")
      ttyio.echo("{f6}[Q]uit")
      ch = ttyio.inputchar("%s [AEDSQ]: " % (prompt), "ASMHQ", "Q")
      if ch == "Q":
        ttyio.echo("quit")
        done = True
        break
      elif ch == "P":
        p = bbsengine.inputpassword("password: ", mask="X")
        attributes["password"] = p
      elif ch == "A":
        if "address" in attributes:
          address = attributes["address"]
        else:
          address = None
        attributes["address"] = ttyio.inputstring("address: ", address, noneok=True)
      elif ch == "H":
        if "host" in attributes:
          default = attributes["host"]
        else:
          default = "merlin.zoidtechnologies.com"
        host = ttyio.inputstring("host: ", default)
        attributes["host"] = host

      elif ch == "S":
        ch = ttyio.inputchar("Status [S]uspend [A]ctive: ", "SA", noneok=True)
        if ch == "S":
          suspenduntil = bbsengine.inputdate("Suspend until: ")
          attributes["suspenduntil"] = suspenduntil
          attributes["status"] = "suspend"
        elif ch == "A":
          ttyio.echo("Active")
          attributes["status"] = "active"
          if "suspenduntil" in attributes:
            del attributes["suspenduntil"]

    ttyio.echo("_editemail.100: attributes=%r" % (attributes), interpret=False)
    return
  def delete():
    pass
  def edit():
    pass
  def add():
    newattributes = _editemail(args, attributes={}, prompt="email.add")
    ttyio.echo("email.add.100: newattributes=%r" % (newattributes), interpret=False)
    return
  def summary():
    pass
