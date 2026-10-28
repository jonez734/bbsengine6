"""The channel service keeps the login role.

bed runs each authenticated request under the member's database role. Channel records are
engine-owned and gated by the channel access rules, so every connection in the channel service
passes set_role=False and ignores the role set for the request.
"""

from __future__ import annotations

import re
from pathlib import Path

import bbsengine6.services.channel as channel_module


def test_channel_service_connections_keep_the_login_role():
    src = Path(channel_module.__file__).read_text(encoding="utf-8")
    calls = re.findall(r"database\.connect\(([^)]*)\)", src)
    assert calls, "expected database.connect calls in the channel service"
    assert all("set_role=False" in c for c in calls), f"connections without set_role=False: {calls}"
