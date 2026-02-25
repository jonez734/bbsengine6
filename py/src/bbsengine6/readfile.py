from . import io

def readfile(filename, escape=True):
    with open(filename, "r") as fp:
        buf = fp.read()
        if buf is None:
            break

