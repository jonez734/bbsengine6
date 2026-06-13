# fileops.py
# File I/O operations for the editor

from .state import EditorBuffer, BufferLine, EditorState


def load_file(filepath: str) -> EditorBuffer:
    lines: list[BufferLine] = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.rstrip("\n\r")
                lines.append(
                    BufferLine(
                        text=line,
                        soft_wrap=False,
                        group_id=None,
                    )
                )
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return EditorBuffer(lines=lines)


def save_file(state: EditorState, **kwargs) -> bool:
    if state.filepath is None:
        return False

    try:
        with open(state.filepath, "w") as f:
            for line in state.buffer.lines:
                if line.read_only:
                    continue
                text = line.text
                if text.endswith("{f6}"):
                    text = text[:-3]
                f.write(text + "\n")
        state.modified = False
        return True
    except Exception:
        return False


def get_content(state: EditorState, **kwargs) -> str:
    lines = []
    for line in state.buffer.lines:
        text = line.text
        if text.endswith("{f6}"):
            text = text[:-3]
        lines.append(text)
    return "\n".join(lines)
