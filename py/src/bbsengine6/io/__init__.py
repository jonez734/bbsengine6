###from .output import *
from .input import *
###from . import echovars
from . import terminal # from .terminal import *
from . import util

from .echo import echo, echo_file, echo_iter, getvar, setvar
from .inputstring import inputstring
from .input import inputboolean, inputinteger, inputchoice
from .lib import *

getterminalwidth = terminal.columns
getterminalheight = terminal.lines

savecursor = terminal.savecursor
restorecursor = terminal.restorecursor

###getvariable = echo.getvar
###setvariable = echo.setvar
###clearvariables = clearvar = echovars.clear

#_streamin = sys.stdin
#_streamout = sys.stdout

def init(args=None, **kwargs):
    return True
