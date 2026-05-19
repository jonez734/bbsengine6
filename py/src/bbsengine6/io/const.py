ESC = "\x1b"  # \x9b
CSI = f"{ESC}["
OSC = f"{ESC}]"
BEL = "\007"
ST = f"{ESC}\\"  # String Terminator (ECMA-48)
ETX = "\x03"  # ctrl-c
EOF = "\x04"  # ctrl-d

MAX_TERMINAL_WIDTH = None  # actual terminal width
FALLBACK_TERMINAL_WIDTH = 100

DEFAULT_PALETTE_NAME = "c64"

ECHO_END = "\n"

# Input timeout for interactive string editing (in seconds)
INPUTSTRING_GETCH_TIMEOUT = 0.015

# Command history defaults (matches GNU readline)
INPUTSTRING_DEFAULT_HISTORY_SIZE = 500          # GNU readline default
INPUTSTRING_DEFAULT_PAGESIZE = 10               # Characters to jump per page
INPUTSTRING_INSERT_MODE_INDICATOR = "[INS]"    # Shown when in insert mode
INPUTSTRING_OVERWRITE_MODE_INDICATOR = "[OVR]" # Shown when in overwrite mode
