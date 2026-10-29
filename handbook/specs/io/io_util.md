# bbsengine6.io.util Specification

## Overview

`util.py` writes log entries. By default it sends them to syslog.

## Dependencies

- `logging`: Python standard library
- `logging.handlers`: `SysLogHandler`

## Functions

### `logentry(message, level=logging.INFO, *, handler=None, formatter=None, logger_name="asimov")`

Writes one log entry.

**Parameters:**
- `message`: the log message
- `level`: an `int` logging level, or one of the strings below (default: `logging.INFO`)
- `handler`: a `logging.Handler` to use instead of the default (default: `None`)
- `formatter`: a `logging.Formatter` to use instead of the default (default: `None`)
- `logger_name`: the logger the entry is written to (default: `"asimov"`)

**Level strings:**

| String | Level |
|--------|-------|
| `"debug"` | DEBUG |
| `"info"` | INFO |
| `"warn"`, `"warning"` | WARNING |
| `"error"` | ERROR |
| `"critical"`, `"crit"` | CRITICAL |

An unknown string is not an error: the entry is logged at INFO.

**Behaviour:**
- The logger's level is set to DEBUG, so every level is passed to its handlers.
- The handler is added to the logger only if the logger has no handler of the same
  type. Repeated calls do not stack handlers.
- The formatter is set on the handler on every call.

## Defaults

- **Handler:** `SysLogHandler(address="/dev/log")`
- **Formatter:** `%(name)s[%(process)d]: %(levelname)s %(message)s`
- **Logger:** `"asimov"`

The logger name `"asimov"` is kept from the module's history. The module's docstring
says the default is `"myapp"`; the code uses `"asimov"`. The code is correct here.

## Usage

```python
from bbsengine6.io.util import logentry
import logging

logentry("Something happened", "info")
logentry("An error", "error")
logentry("Debug detail", level=logging.DEBUG)
```

## Note on syslog

The default handler writes to `/dev/log`. On this system that path is a symlink to the
systemd journal. The behaviour when no socket is present was not tested, so the spec
does not state it. Pass `handler=` to write somewhere else.
