import sys
from bbsengine6 import io, bottombar

term = io.terminal.report()
io.echo(str(term))
bottombar.init()

def inputstring_box(prompt, oldvalue="", *, header="", max_width=25, max_len=255, bottombar=True, **kwargs):
    title = kwargs.get("title", "")
    # The interior is the larger of max_width and the title's width. A title is drawn as
    # "ltee title rtee" inside the top edge, which takes 5 columns beyond the title text.
    title_width = len(title) + 5 if title else 0
    max_width = max(max_width, title_width)
    if title:
        # The titled top edge is ulcorner, hline, ltee, space, title, space, rtee, hlines, urcorner.
        # The box is max_width + 2 wide, so the hlines are whatever is left after those parts.
        trailing = max_width - len(title) - 5
        # {hline:0} draws one hline (a count of 0 is not "none"), so leave the run out when it is 0.
        run = f"{{hline:{trailing}}}" if trailing > 0 else ""
        io.echo(f"{{acscolor}}{{ulcorner}}{{hline}}{{ltee}} {{promptcolor}}{title}{{acscolor}} {{rtee}}{run}{{urcorner}}")
    else:
        io.echo(f"{{acscolor}}{{acs:ulcorner}}{{acs:hline:{max_width}}}{{acs:urcorner}}")
    io.echo(f"{{acs:vline}}{' '*max_width}{{acs:vline}}")
    io.echo(f"{{acs:llcorner}}{{acs:hline:{max_width}}}{{acs:lrcorner}}", end="")
    io.echo(f"{{cursorup}}{{cha:1}}{{cursorright:2}}", end="")
    buf = io.inputstring(prompt, oldvalue, max_width=max_width - 1, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf


if io.terminal.has_ansi():
    io.echo("ANSI enabled")
else:
    io.echo("ANSI disabled")

io.echo(inputstring_box(f"prompt: ", "", title="", max_width=25))

bottombar.shutdown()
