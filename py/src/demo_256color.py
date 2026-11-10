from bbsengine6 import io
from bbsengine6.io.palette import rgb_to_hex

STEPS = 128
for step in range(STEPS):
    # Linear fade from 255 down to 0 over all steps, so no step is black before the last one.
    level = round(255 * (STEPS - 1 - step) / (STEPS - 1))
    r, g, b = level, level, level
    io.echo(f"test {{rgb:{r},{g},{b}}}{rgb_to_hex(r, g, b)}test ")
