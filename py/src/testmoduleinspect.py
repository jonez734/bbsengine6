import bbsengine6 as bbsengine


def access(args, op, **blah):
    return True


def buildargs(args, **kw):
    return None


def init(args, **kw):
    return True


def main(args, **kw):
    return True


if __name__ == "__main__":
    m = bbsengine.module.check(None, "testmoduleinspect")
#    m = bbsengine.module.load(None, "testmoduleinspect")
#    g = eval("m.access")
#    ttyio.echo(f"{g=}", level="debug")
#    print(g)
#    sig = signature(g)
#    print(sig.parameters["args"])
#    if "args" in sig.parameters:
#        print("YES!")
#    print("foo")
