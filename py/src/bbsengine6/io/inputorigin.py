"""The shared input origin and window rule for the input functions.

An input function draws its prompt, then reads the engine's tracked cursor to find where the input
starts. The caller may have drawn a box and moved the cursor with cursor commands first, so the
tracked position is the only reliable origin. inputstring, inputchoice and inputcompleter all use
:func:`input_origin`, so they agree on where the input starts and how wide its window is.

Rules:
- The origin is the tracked cursor after the prompt. A prompt with an {f6} leaves the origin on the
  row below, at the tracked column (the indent, 0 by default).
- Without a break the prompt shares the input row, so the window is ``max_width`` minus the prompt's
  visible width. After an {f6} the input has its own row and the window is the full ``max_width``.
- If the tracked position is not usable (no terminal), the origin falls back to the start position
  plus the prompt's visible width, and the window uses the same rule.
"""

from __future__ import annotations

from .echo import rendered_length


def input_origin(
    prompt: str, start_row: int, start_col: int, max_width: int
) -> tuple[int, int, int]:
    """Return ``(row, col, window)`` for the input that follows ``prompt``.

    Call this after the prompt has been drawn. ``col`` is 1-based, like ``{curpos}``.
    """
    from .common import _terminal_state

    # Read the tracked position first. rendered_length() tokenises the prompt, and tokenising can
    # move the tracked cursor (the {f6} in a prompt), so the position must be read before it runs.
    row = getattr(_terminal_state, "cursor_row", None)
    col = getattr(_terminal_state, "cursor_col", None)
    prompt_len = int(rendered_length(prompt))
    if isinstance(row, int) and isinstance(col, int) and row >= 1 and col >= 0:
        # The tracked column is 0 at the start of a row (after an {f6}). Convert to 1-based.
        origin_row, origin_col = row, max(col, 1)
    else:
        origin_row, origin_col = start_row, start_col + prompt_len

    # The prompt is on the input row only when no break moved the origin off the start row.
    on_prompt_row = origin_row == start_row
    window = max(1, max_width - prompt_len) if on_prompt_row else max(1, max_width)
    return origin_row, origin_col, window
