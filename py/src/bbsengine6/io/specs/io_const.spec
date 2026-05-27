# asimov.io.const Specification

## Overview

`const.py` defines terminal and I/O constants used throughout the io module.

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `ESC` | `\x1b` | Escape character |
| `CSI` | `\x1b[` | Control Sequence Introducer |
| `OSC` | `\x1b]` | Operating System Command |
| `BEL` | `\x07` | Bell character |
| `ETX` | `\x03` | End of Text (Ctrl+C) |
| `EOF` | `\x04` | End of File (Ctrl+D) |
| `MAX_TERMINAL_WIDTH` | `None` | Terminal width limit (None = no limit) |
| `FALLBACK_TERMINAL_WIDTH` | `100` | Default width when unable to detect |
| `DEFAULT_PALETTE_NAME` | `"c64"` | Default color palette |
| `ECHO_END` | `"\n"` | Default line ending for echo |

## Usage

Import constants directly:
```python
from asimov.io.const import ESC, CSI, BEL
```
