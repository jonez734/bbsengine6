# Simple test - just curly braces in strings
from bbsengine6 import message
r = message.render_template("Hello {name}!", {"name": "Alice"})
print("Result:", r)
