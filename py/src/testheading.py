import ttyio6 as ttyio
import bbsengine6 as bbsengine

buf = "projup #8237 - fix off-by-one glitch in bbsengine6.util.heading()"
print(len(buf))
bbsengine.util.heading(buf)
buf = "&projup #8237 - fix off-by-one glitch in bbsengine6.util.heading()"
print(len(buf))
bbsengine.util.heading(buf)
