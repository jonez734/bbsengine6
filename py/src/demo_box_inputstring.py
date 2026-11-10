import sys
from bbsengine6 import io, bottombar

term = io.terminal.report()
io.echo(str(term))
bottombar.init()

def inputstring_box(prompt, oldvalue="", *, header="", max_width=25, max_len=255, bottombar=True, **kwargs):
    toplinewidth = max_width + len(prompt) - 4
    io.echo(f"{toplinewidth=}", level="debug")
    title = kwargs.get("title", "")
    if len(title) > 0:
        io.echo(f"{{acscolor}}{{ulcorner}}{{hline}}{{ltee}} {{promptcolor}}{title}{{acscolor}} {{rtee}}{{hline:{toplinewidth}}}{{urcorner}}")
    else:
        io.echo(f"{{acscolor}}{{acs:ulcorner}}{{acs:hline:{max_width}}}{{acs:urcorner}}")
    io.echo(f"{{acs:vline}}{' '*max_width}{{acs:vline}}")
    io.echo(f"{{acs:llcorner}}{{acs:hline:{toplinewidth}}}{{acs:lrcorner}}", end="")
    io.echo(f"{{cursorup}}{{cha:1}}{{cursorright:2}}", end="")
    buf = io.inputstring("", oldvalue, max_width=max_width - 1, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf


if io.terminal.has_ansi():
    io.echo("ANSI enabled")
else:
    io.echo("ANSI disabled")

io.echo(inputstring_box(f"", "", title="moniker", max_width=14))

bottombar.shutdown()
