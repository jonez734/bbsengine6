# asimov.io.keymap Specification

## Overview

`keymap.py` defines the mapping from ANSI escape sequences to logical key names. This is a minimal subset used by `getch.py`.

## Dependencies

- `const.py`: ESC

## KEY_MAP

Dictionary mapping ANSI escape sequences to key names.

| Escape Sequence | Key Name |
|----------------|----------|
| `\x1b[A` | `KEY_UP` |
| `\x1b[B` | `KEY_DOWN` |
| `\x1b[C` | `KEY_RIGHT` |
| `\x1b[D` | `KEY_LEFT` |
| `\x1b[H` | `KEY_HOME` |
| `\x1b[F` | `KEY_END` |
| `\x1b[2~` | `KEY_INSERT` |
| `\x1b[3~` | `KEY_DELETE` |
| `\x1b[5~` | `KEY_PAGEUP` |
| `\x1b[6~` | `KEY_PAGEDOWN` |
| `\x1bOP` | `KEY_F1` |
| `\x1bOQ` | `KEY_F2` |
| `\x1bOR` | `KEY_F3` |
| `\x1bOS` | `KEY_F4` |
| `\x1b[15~` | `KEY_F5` |
| `\x1b[17~` | `KEY_F6` |
| `\x1b[18~` | `KEY_F7` |
| `\x1b[19~` | `KEY_F8` |
| `\x1b[20~` | `KEY_F9` |
| `\x1b[21~` | `KEY_F10` |
| `\x1b[23~` | `KEY_F11` |
| `\x1b[24~` | `KEY_F12` |

## Note

This is a minimal keymap. A complete solution would include:
- Application cursor keys (DECCKM mode)
- Modified keys (Shift+, Ctrl+, Alt+ variants)
- More function key formats
- Navigation keys (Home, End, etc. alternatives)
