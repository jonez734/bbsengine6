from bbsengine6 import io, screen

screen.init()

for x in ("foo", "bar", "baz", "bing"):
    screen.setbottombar(x, stack=True)
    io.inputboolean("continue? [Yn]: ")

io.echo("blah")

for x in ("foo", "bar", "baz", "bing"):
    screen.poparea()
    io.inputboolean("continue? [Yn]: ")
