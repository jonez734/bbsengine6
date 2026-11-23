"""demo_authenticate: one frame holds the moniker and password fields.

The frame is drawn with two interior rows. The moniker is read on the first row; its Enter leaves the cursor one row below
the field, which after_field() records, so the password row is reached with a relative move. The password is read masked,
with nothing shown as it is typed.
"""

from bbsengine6 import bottombar, io
from bbsengine6.util import draw_frame, inputpassword

WIDTH = 25
#: Labels padded to one width so the values start in the same column (same as bed's sign-in).
LABEL_MONIKER = "moniker:  "
LABEL_PASSWORD = "password: "
TITLE = "zoid6 auth"


def main() -> None:
    bottombar.init()
    try:
        frame = draw_frame(TITLE, WIDTH, height=2)
        # Paint every child's label before the first read, then move back to the first child.
        frame.paint_label(0, LABEL_MONIKER)
        frame.paint_label(1, LABEL_PASSWORD)
        frame.place_row(0)
        moniker = io.inputstring("{promptcolor}" + LABEL_MONIKER + "{inputcolor}", "", max_width=WIDTH - 1, bottombar=False)
        frame.after_field()
        if moniker != "":
            frame.place_row(1)
            inputpassword("{promptcolor}" + LABEL_PASSWORD + "{inputcolor}", bottombar=False)

            io.echo("{f6}")
            io.echo(f"signed in as {moniker.strip()}")
        else:
            io.echo("aborted")
    finally:
        bottombar.shutdown()


if __name__ == "__main__":
    main()
