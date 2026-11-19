"""demo_authenticate: the sign-in frame grows from a moniker box to a password box.

A frame is drawn with the moniker field inside it. Enter accepts the moniker, and the frame is grown with a password box
under it at the same width (the join between the two is written between save and restore). The password is read masked,
with nothing shown as it is typed.
"""

from bbsengine6 import bottombar, io
from bbsengine6.util import Child, draw_frame, extend_frame, inputpassword

WIDTH = 25
TITLE = "zoid6 auth"


def main() -> None:
    bottombar.init()
    try:
        frame = draw_frame(TITLE, WIDTH, children=[Child(title="moniker")])
        moniker_field = frame.children[0]
        io.echo(f"{{curpos:{moniker_field.top},{moniker_field.column}}}", end="")
        moniker = io.inputstring("{promptcolor}moniker: {inputcolor}", "", max_width=WIDTH - 1, bottombar=False)

        frame = extend_frame(frame, Child(title="password"), width=WIDTH)
        password_field = frame.children[-1]
        io.echo(f"{{curpos:{password_field.top},{password_field.column}}}", end="")
        inputpassword("{promptcolor}password: {inputcolor}", bottombar=False)

        io.echo("{f6}")
        io.echo(f"signed in as {moniker.strip()}")
    finally:
        bottombar.shutdown()


if __name__ == "__main__":
    main()
