import bbsengine6.io

choice = bbsengine6.io.inputchoice("prompt", "ABC", "A", rewriteprompt=True)
print(f"{choice=}")
bbsengine6.io.echo(f"{{/all}}")

