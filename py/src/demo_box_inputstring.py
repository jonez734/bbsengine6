import sys
from bbsengine6 import io, bottombar


io.echo(str(io.terminal.terminal_report()))

bottombar.init()

def inputstring_box(prompt, oldvalue="", *, max_width=25, max_len=255, **kwargs):
    io.echo(f"{{acscolor}}{{acs:ulcorner}}{{acs:hline:{max_width+1}}}{{acs:urcorner}}")
    io.echo(f"{{acs:vline}}{' '*max_width}{{acs:vline}}")
    io.echo(f"{{acs:llcorner}}{{acs:hline:{max_width+1}}}{{acs:lrcorner}}", end="")
    io.echo(f"{{cursorup}}{{cha:1}}{{cursorright:2}}", end="")
    buf = io.inputstring(prompt, max_width=max_width, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf

io.echo(inputstring_box(f"{{promptcolor}}inputstring_box: {{inputcolor}}", "NEEDINFO"))
