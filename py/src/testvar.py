from bbsengine6 import io

# this intentionally sets up a recursive value.. it will give a traceback after a few seconds
io.setvar("foo", "{bar}")
io.setvar("bar", "{foo}")

io.echo("{foo}")
