#import sys

from .output import *
from .input import *
from . import vars
from . import terminal # from .terminal import *

from .lib import *

getterminalwidth = terminal.columns
getterminalheight = terminal.lines

savecursor = terminal.savecursor
restorecursor = terminal.restorecursor

getvariable = getvar = vars.get
setvariable = setvar = vars.set
clearvariables = clearvar = vars.clear

#_streamin = sys.stdin
#_streamout = sys.stdout

def init(args=None, **kw):
    return True
