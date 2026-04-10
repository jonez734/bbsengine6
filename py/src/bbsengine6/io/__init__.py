# io - terminal I/O module

from .echo import (
    echo,
    echo_file,
    echo_traceback,
    rendered_length,
    setvar,
    getvar,
    register_emoji,
    register_emojis,
)
from .common import get_cursor_position
from .inputstring import inputstring
from .inputinteger import inputinteger
from .inputboolean import inputboolean
from .inputchoice import inputchoice
from .getch import (
    getch_str as getch,
    KeyEvent,
    EventHandler,
    register_key_event_handler,
    unregister_key_event_handler,
    get_registered_handlers,
    start_event_dispatcher,
    stop_event_dispatcher,
    is_event_dispatcher_running,
    set_event_dispatcher_timeout,
    get_event_queue,
    is_event_queue_empty,
    clear_event_queue,
    set_event_error_handler,
    get_key_event_history,
    clear_key_event_history,
)

inputchar = inputchoice

__all__ = [
    "echo",
    "echo_file",
    "echo_traceback",
    "rendered_length",
    "get_cursor_position",
    "setvar",
    "getvar",
    "register_emoji",
    "register_emojis",
    "inputstring",
    "inputinteger",
    "inputboolean",
    "inputchoice",
    "inputchar",
    "getch",
    "KeyEvent",
    "EventHandler",
    "register_key_event_handler",
    "unregister_key_event_handler",
    "get_registered_handlers",
    "start_event_dispatcher",
    "stop_event_dispatcher",
    "is_event_dispatcher_running",
    "set_event_dispatcher_timeout",
    "get_event_queue",
    "is_event_queue_empty",
    "clear_event_queue",
    "set_event_error_handler",
    "get_key_event_history",
    "clear_key_event_history",
]
