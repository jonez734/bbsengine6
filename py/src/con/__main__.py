import ttyio5 as ttyio
import bbsengine6 as bbsengine
from bbsengine6 import util

util.title("console")
buf = ttyio.inputstring("con: ", "")
print(buf)
