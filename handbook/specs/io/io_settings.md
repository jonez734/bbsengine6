# bbsengine6.io settings

**File:** `bbsengine6/io/settings.py`

The timing and size values that `bbsengine6.io` uses are settings, not constants. A host sets them
from the `io` section of its config. Each setting has a default: the value the module used before it
was configurable.

## Settings

| Setting | Default | Kind | Used by |
|---------|---------|------|---------|
| `query_settle_seconds` | `0.25` | seconds | `common.query_terminal`: how long the tty is read after a probe's timeout. |
| `esc_tail_wait_seconds` | `0.05` | seconds | `getch`: how long to wait for the rest of a split escape sequence. |
| `inputstring_getch_timeout_seconds` | `0.015` | seconds | `inputstring`: how long each pass of its loop waits for a key. |
| `inputstring_history_size` | `500` | count | `inputstring`: entries kept when `history=True`. Matches GNU readline. |
| `inputstring_pagesize` | `10` | count | `inputstring`: characters moved by PAGE UP and PAGE DOWN. |
| `paste_max_bytes` | `65536` | count | `getch`: characters of a paste kept; longer pastes are cut. |

Seconds must be a positive number. Counts must be a positive integer. A bool, string, or zero is
rejected.

## Configuration

```python
from bbsengine6.io import settings
settings.configure({"inputstring_pagesize": 4, "_comment": "ignored"})
```

`configure(section)` takes the `io` object of a config, not the whole file. Keys starting with `_` are
comments. An unknown key or a bad value raises `ValueError` before anything changes. Settings are read
when they are used, so a value set after import still takes effect at the next use.

bed applies its config's `io` section at startup (`_apply_io_config`). zoid6's packaged `zoid6.json`
carries the section with the defaults.

## Not settings

These stay in code, because they must match the terminal or a file format exactly, or they are
identifiers: protocol sequences (`CSI`, `OSC`, `ST`, the DA and XTGETTCAP requests), the terminfo
format tables, the key maps, `ECHO_END`, `UNUSABLE_TERMS`, and the mouse modes.

Display defaults (`MAX_WIDTH`, `FALLBACK_TERMINAL_WIDTH`, `DEFAULT_TERM`, `DEFAULT_PALETTE_NAME`) and
the inputstring bottom-bar wording are also still constants. They affect terminal detection and
translation, so they need their own review before they move.
