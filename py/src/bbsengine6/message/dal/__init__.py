# bbsengine6/message/dal/__init__.py
#
# DAL - Data Access Layer for bbsengine6.message.
#
# One module per engine.__message* table family. Pure Postgres I/O;
# no policy, no enable/disable gating, no rate-limit checks, no
# recipient expansion. Services in ``bbsengine6.message.service``
# call into DAL methods; DAL executes queries via
# ``bbsengine6.database``. Mirrors ``casino/src/casino/dal/__init__.py``.
#
# Public entry points (re-exported for convenience):
#
#   from bbsengine6.message.dal import messages
#   from bbsengine6.message.dal import recipients
#   from bbsengine6.message.dal import groups
#   from bbsengine6.message.dal import blocking
#   from bbsengine6.message.dal import ratelimit
#   from bbsengine6.message.dal import types

from __future__ import annotations

from bbsengine6.message.dal import (  # noqa: F401
    blocking,
    groups,
    messages,
    ratelimit,
    recipients,
    types,
)
