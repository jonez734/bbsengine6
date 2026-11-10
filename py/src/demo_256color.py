from bbsengine6 import io
from bbsengine6.io.palette import rgb_to_hex

r, g, b = 255, 255, 255
for x in range(0, 128):
    r, g, b = (max(0, min(255, c - x)) for c in (r, g, b))
    io.echo(f"{{rgb:{r},{g},{b}}}{rgb_to_hex(r, g, b)} ")
