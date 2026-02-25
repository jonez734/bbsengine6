from bbsengine6 import io
#from asimov.io import util
#from asimov.io.echo import echo
#from asimov.io.getch import getch_str as getch
#from asimov.io.inputboolean import inputboolean

io.util.screen_init() ### screen.init()
io.util.setbottombar("left side of bar", "right side of bar")
io.echo("{f6}", end="")
for i in range(0, 20):
    io.echo(f"blah {i}{{f6}}blah{{f6}}blah{{f6:2}}")
try:
    io.inputstring("prompt> ")
finally:
    io.echo("{savecursor}{decstbm}{restorecursor}", flush=True)
