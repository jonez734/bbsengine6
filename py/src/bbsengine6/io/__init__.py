from .output import *
from .input import *
from . import vars
from . import terminal # from .terminal import *

from .lib import *

getterminalwidth = terminal.width
getterminalheight = terminal.height

savecursor = terminal.savecursor
restorecursor = terminal.restorecursor

getvariable = getvar = vars.get
setvariable = setvar = vars.set
clearvariables = clearvar = vars.clear
