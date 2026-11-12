ESC = "\x1b"  # \x9b
CSI = f"{ESC}["
OSC = f"{ESC}]"
BEL = "\007"
ST = f"{ESC}\\"  # String Terminator (ECMA-48)
ETX = "\x03"  # ctrl-c
EOF = "\x04"  # ctrl-d

FALLBACK_TERMINAL_WIDTH = 100

DEFAULT_PALETTE_NAME = "c64"

ECHO_END = "\n"

# Input timeout for interactive string editing (in seconds)

# Command history defaults (matches GNU readline)
INPUTSTRING_INSERT_MODE_INDICATOR = "[INS]"  # Shown when in insert mode
INPUTSTRING_OVERWRITE_MODE_INDICATOR = "[OVR]"  # Shown when in overwrite mode
INPUTSTRING_ACCEPT_HINT = "press enter to accept value"  # Bottom-bar left side while a prompt waits
