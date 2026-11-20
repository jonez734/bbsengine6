import sys
from bbsengine6 import io, bottombar
from bbsengine6.util import draw_box, inputpassword

#term = io.terminal.report()
#io.echo(str(term))
#bottombar.init()

def inputstring_box(prompt, oldvalue="", *, header="", width=25, max_len=255, bottombar=True, height=1, **kwargs):
    title = kwargs.get("title", "")
    # draw_box widens the box to fit the title; widen here too so inputstring gets the same width.
    if title:
        width = max(width, len(title) + 5)
    draw_box(title, width, height)
    # draw_box leaves the cursor at the end of the bottom edge; move it to the first interior row.
    io.echo(f"{{cursorup:{max(2, height)}}}{{cha:1}}{{cursorright:2}}", end="")
    buf = io.inputstring(prompt, oldvalue, max_width=width - 1, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf


def inputpassword_box(prompt, oldvalue="", *, header="", width=25, max_len=255, bottombar=True, height=1, **kwargs):
    title = kwargs.get("title", "")
    # draw_box widens the box to fit the title; widen here too so inputstring gets the same width.
    if title:
        width = max(width, len(title) + 5)
    io.echo(f"{{cursorup:4}}", end="")
    draw_box(title, width, height)
    # draw_box leaves the cursor at the end of the bottom edge; move it to the first interior row.
    io.echo(f"{{cursorup:{max(2, height)}}}{{cha:1}}{{cursorright:2}}", end="")
    buf = inputpassword(prompt, oldvalue, max_width=width - 1, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf


if io.terminal.has_ansi():
    io.echo("ANSI enabled")
else:
    io.echo("ANSI disabled")

moniker = inputstring_box(f"{{promptcolor}}moniker: {{inputcolor}}", "", title="zoid6 auth", width=25, bottombar=False)
password = inputpassword_box(f"{{promptcolor}}password: {{inputcolor}}", "", title=f"casino auth {moniker}", bottombar=False)

#bottombar.shutdown()
