# state.py
# Editor state dataclasses

from dataclasses import dataclass, field
from enum import Enum, auto


class Justify(Enum):
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


@dataclass
class BufferLine:
    text: str
    justify: Justify = Justify.LEFT
    read_only: bool = False
    soft_wrap: bool = True
    group_id: int | None = None


@dataclass
class EditorBuffer:
    lines: list[BufferLine] = field(default_factory=list)


@dataclass
class EditorState:
    filepath: str | None = None
    buffer: EditorBuffer = field(default_factory=EditorBuffer)
    cursor_x: int = 0
    cursor_y: int = 0
    scroll_offset: int = 0
    modified: bool = False
    ctrl_k_mode: bool = False
    width: int = 0
    height: int = 0
    test_mode: bool = False


def create_editor_state(
    filepath: str | None = None,
    width: int = 0,
    height: int = 0,
    test_mode: bool = False,
) -> EditorState:
    return EditorState(
        filepath=filepath,
        buffer=EditorBuffer(),
        cursor_x=0,
        cursor_y=0,
        scroll_offset=0,
        modified=False,
        ctrl_k_mode=False,
        width=width,
        height=height,
        test_mode=test_mode,
    )
