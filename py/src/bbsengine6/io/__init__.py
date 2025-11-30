#import sys

###from .output import *
from .input import *
###from . import echovars
from . import terminal # from .terminal import *

from .echo import echo, echo_file, echo_iter

from .lib import *

getterminalwidth = terminal.columns
getterminalheight = terminal.lines

savecursor = terminal.savecursor
restorecursor = terminal.restorecursor

getvariable = getvar = echovars.get
setvariable = setvar = echovars.set
clearvariables = clearvar = echovars.clear

#_streamin = sys.stdin
#_streamout = sys.stdout

def init(args=None, **kw):
    return True
