"""The bed gate reports bed's state the same way the app's probe does."""

from unittest.mock import patch

import pytest

from tests import _bed_gate


@pytest.mark.unit
def test_gate_reports_down_when_probe_fails():
    with patch("bed.client.probe.probe_bed", return_value=False):
        assert _bed_gate.bed_is_running() is False


@pytest.mark.unit
def test_gate_reports_up_when_probe_succeeds():
    with patch("bed.client.probe.probe_bed", return_value=True):
        assert _bed_gate.bed_is_running() is True


@pytest.mark.unit
def test_bed_fixture_skips_when_down():
    with patch.object(_bed_gate, "bed_is_running", return_value=False):
        with pytest.raises(pytest.skip.Exception, match="bed is not running"):
            _bed_gate.bed_running.__wrapped__()
