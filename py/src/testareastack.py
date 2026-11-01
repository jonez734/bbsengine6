from bbsengine6 import io, bottombar

bottombar.init()

for x in ("foo", "bar", "baz", "bing"):
    bottombar.push(left=x)
    io.inputboolean("continue? [Yn]: ")

io.echo("blah")

for x in ("foo", "bar", "baz", "bing"):
    bottombar.pop()
    io.inputboolean("continue? [Yn]: ")
