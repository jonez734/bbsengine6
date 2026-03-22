from bbsengine6 import io


def main():
    io.echo(f"one fish, two fish, {{red}}red fish, {{blue}}blue fish{{/all}}")
    io.echo(f"{{var:normalcolor}}normal{{/all}}")


if __name__ == "__main__":
    main()
