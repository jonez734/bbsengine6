import ttyio6 as ttyio
import bbsengine6 as bbsengine


bbsengine.screen.init()

for x in ("foo", "bar", "baz", "bing"):
    bbsengine.screen.setarea(x, stack=True)
    ttyio.inputboolean("continue? [Yn]: ")

ttyio.echo("blah")

for x in ("foo", "bar", "baz", "bing"):
    bbsengine.screen.poparea()
    ttyio.inputboolean("continue? [Yn]: ")

