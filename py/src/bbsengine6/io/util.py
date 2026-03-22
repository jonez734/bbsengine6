# ---------
# logging
# ---------
import logging
import logging.handlers

# default syslog handler
default_handler = logging.handlers.SysLogHandler(address="/dev/log")
default_formatter = logging.Formatter(
    "%(name)s[%(process)d]: %(levelname)s %(message)s"
)
default_handler.setFormatter(default_formatter)


def logentry(
    message,
    level: int | str = logging.INFO,
    *,
    handler=None,
    formatter=None,
    logger_name="asimov",
):
    """
    Write a log entry to syslog (by default), with optional handler/formatter overrides.

    Args:
        message (str): The log message.
        level (int): Logging level (default=logging.INFO).
        handler (logging.Handler, optional): Custom logging handler.
        formatter (logging.Formatter, optional): Custom formatter.
        logger_name (str): Name for the logger (default="myapp").
    """

    h = handler or default_handler
    f = formatter or default_formatter

    # Ensure formatter is applied
    h.setFormatter(f)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # capture all levels
    if not any(isinstance(x, type(h)) for x in logger.handlers):
        logger.addHandler(h)

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "crit": logging.CRITICAL,
        #        "exception":logging.EXCEPTION,
    }

    if level in levels:
        level = levels[level]
    else:
        level = logging.INFO

    logger.log(level, message)
    return
