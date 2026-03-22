# Dictionary to map ANSI escape sequences to logical key names
# This is a MINIMAL subset—a robust solution requires a much larger map.

from .const import ESC

KEY_MAP = {
    f"{ESC}[A": "KEY_UP",
    f"{ESC}[B": "KEY_DOWN",
    f"{ESC}[C": "KEY_RIGHT",
    f"{ESC}[D": "KEY_LEFT",
    f"{ESC}[H": "KEY_HOME",
    f"{ESC}[F": "KEY_END",
    f"{ESC}[2~": "KEY_INSERT",
    f"{ESC}[3~": "KEY_DELETE",
    f"{ESC}[5~": "KEY_PAGEUP",
    f"{ESC}[6~": "KEY_PAGEDOWN",
    f"{ESC}OP": "KEY_F1",
    #    f"{ESC}OP": "KEY_HELP", # PF1
    f"{ESC}OQ": "KEY_F2",
    f"{ESC}OR": "KEY_F3",
    f"{ESC}OS": "KEY_F4",
    f"{ESC}[15~": "KEY_F5",
    f"{ESC}[17~": "KEY_F6",
    f"{ESC}[18~": "KEY_F7",
    f"{ESC}[19~": "KEY_F8",
    f"{ESC}[20~": "KEY_F9",
    f"{ESC}[21~": "KEY_F10",
    f"{ESC}[23~": "KEY_F11",
    f"{ESC}[24~": "KEY_F12",
}
