from bbsengine6 import io, screen

screen.init()
for x in range(1, 100+1):
    screen.updateprogress(x, 100)
    io.echo("{wait:1}", end="", flush=True)
io.echo("{/all}")
