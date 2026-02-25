from bbsengine6 import io

width = 80

for section in range(1, width//10+1):
    io.echo(f".........{section}", end="")
io.echo("{f6}", end="")
for sesion in range(1, width//10+1):
    io.echo(f"*********0", end="")
io.echo("{f6}", end="")

#.........1......... 2......... 3......... 4......... 5......... 6......... 7......... 8
