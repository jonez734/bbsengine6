import sys
from bbsengine6 import io, bottombar
from bbsengine6.util import draw_frame

#io.echo("{f6:3}{cursorup:3}")
#bottombar.init()

def inputstring_box(prompt, oldvalue="", *, header="", width=25, max_len=255, bottombar=True, height=1, **kwargs):
    title = kwargs.get("title", "")
    # The field's place comes from the frame's geometry, the same as demo_authenticate.
    frame = draw_frame(title, width)
    frame.place_field()
    buf = io.inputstring(prompt, oldvalue, max_width=frame.width - 1, bottombar=bottombar, **kwargs)
    io.echo(f"{{f6}}")
    return buf


if io.terminal.has_ansi():
    io.echo("ANSI enabled")
else:
    io.echo("ANSI disabled")

io.echo(inputstring_box(f"{{promptcolor}}moniker: {{inputcolor}}", "", title="zoid6 auth", width=25, bottombar=False))
io.echo("{f6}")

#bottombar.shutdown()
