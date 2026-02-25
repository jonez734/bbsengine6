import bbsengine6 as bbsengine

def main():
    bbsengine.io.echo(f"{{savecursor}}cursor saved")
    bbsengine.io.echo(f"{bbsengine.io.terminal.cursorpositions=}")
    bbsengine.io.echo(f"{{restorecursor}}")
    bbsengine.io.echo(f"{bbsengine.io.terminal.cursorpositions=}")

if __name__ == "__main__":
    main()
