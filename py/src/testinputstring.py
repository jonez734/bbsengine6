import bbsengine6.io

try:
    buf = bbsengine6.io.inputstring("prompt: ", help="this is a test")
    print(buf)
except KeyboardInterrupt:
    bbsengine6.io.echo("{/all}*INTR*")
except EOFError:
    bbsengine6.io.echo("{/all}*EOF*")
