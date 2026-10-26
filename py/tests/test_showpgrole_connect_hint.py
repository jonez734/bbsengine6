"""The 'Connect with' hint names the login role (osuser), never the NOLOGIN data role."""

from unittest.mock import patch

import pytest

from bbsengine6.console import showpgrole


@pytest.mark.unit
def test_connect_hint_uses_the_login_role_not_the_data_role():
    row = {"rolname": "m_lo_test", "loginid": "lo_test", "created_at": None, "last_ack_at": "x"}
    out = []
    with patch.object(showpgrole.io, "echo", side_effect=lambda msg="", **k: out.append(str(msg))), \
         patch.object(showpgrole.util, "heading"):
        showpgrole._render(row, "lo_test")
    text = "\n".join(out)
    assert "-U lo_test" in text, text
    assert "-U m_lo_test" not in text, text

