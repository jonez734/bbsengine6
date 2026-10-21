"""Gate tests that need a running bed server.

bed must be running before bed-dependent tests run. This uses bed's own
``probe_bed`` (the same TCP check the app uses), so the test and the app agree
on whether bed is up. A test marked ``requires_bed`` is skipped with a clear
reason when bed is down. Run ``bed`` (or ``systemctl start bed``) first.
"""

from __future__ import annotations

import types

import pytest


def bed_args():
    """Connection settings for the bed probe (the bed default port)."""
    return types.SimpleNamespace(bed_host="127.0.0.1", bed_port=8765, bed_probe_timeout=0.5)


def bed_is_running() -> bool:
    try:
        from bed.client.probe import probe_bed
    except ImportError:
        return False
    return bool(probe_bed(bed_args()))


@pytest.fixture
def bed_running():
    """Skip the test unless bed is reachable."""
    if not bed_is_running():
        pytest.skip("bed is not running on 127.0.0.1:8765 (start bed before this test)")
    return True
