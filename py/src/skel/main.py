from bbsengine6 import util

#from . import lib

def init(args, **kw:dict) -> bool:
    return True

def access(args, op:str, **kw:dict) -> bool:
    return True

def buildargs(args, **kw:dict):
#    return lib.buildargs(args, **kw)
    return None

def main(args, **kw):
    util.heading("HEADER")
    return True
