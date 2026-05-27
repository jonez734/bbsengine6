# asimov.io.util Specification

## Overview

`util.py` provides logging utilities, primarily for logging to syslog.

## Dependencies

- `logging`: Python standard library
- `logging.handlers`: SysLogHandler

## Functions

### `logentry(message, level=logging.INFO, *, handler=None, formatter=None, logger_name="asimov")`

Write a log entry to syslog (by default).

**Parameters:**
- `message`: The log message
- `level`: Logging level (default: `logging.INFO`)
- `handler`: Custom logging handler (default: SysLogHandler)
- `formatter`: Custom formatter (default: `'%(name)s[%(process)d]: %(levelname)s %(message)s'`)
- `logger_name`: Logger name (default: "asimov")

**Level Aliases:**
| String | Level |
|--------|-------|
| "debug" | DEBUG |
| "info" | INFO |
| "warn"/"warning" | WARNING |
| "error" | ERROR |
| "critical"/"crit" | CRITICAL |

## Default Configuration

- **Handler**: SysLogHandler at `/dev/log`
- **Format**: `%(name)s[%(process)d]: %(levelname)s %(message)s`

## Usage

```python
from asimov.io.util import logentry

logentry("Something happened", "info")
logentry("An error", "error")
logentry("Debug info", level=logging.DEBUG)
```
