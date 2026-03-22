from bbsengine6 import io

# io.echo("this is a test with a normal ending", end="")
# io.echo("this is more text to test wordwrap across echo calls.. it has to be a bit longer", end="")
# io.echo("if wordwrap is to be properly tested", end="")
# io.echo("here's another line to test things properly")
io.echo(
    "{var:promptcolor}prompt color  {var:labelcolor}label color{f6}{inputcolor}input color{f6}{var:optioncolor}option color{/all}",
    end="",
)
io.echo(":smile:")
io.echo(
    "{red}red fish, {blue}blue fish, {orange}orange fish{/all} {invalidcommandhere}"
)
io.echo("test logging message", level="info")
