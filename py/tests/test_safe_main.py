#
# test_safe_main.py - unit tests for bbsengine6.util.safe_main.
#

import os
import sys

import pytest

sys.path.insert(0, "src")

from bbsengine6.util import DANGEROUS_PYTHON_ENV_VARS, safe_main, sanitize_args

pytestmark = pytest.mark.unit


@pytest.fixture
def argv_clean(monkeypatch):
    """Replace sys.argv with a clean baseline for each test."""
    monkeypatch.setattr(sys, "argv", ["prog", "--foo", "bar"])
    return ["--foo", "bar"]


@pytest.fixture
def argv_rejected(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "-X", "foo"])
    return ["-X", "foo"]


class TestHappyPath:
    def test_main_called_with_clean_argv(self, argv_clean, capsys):
        def main():
            return 0

        rc = safe_main(main)
        assert rc == 0
        # sys.argv[1:] should now reflect the cleaned argv.
        assert sys.argv[1:] == ["--foo", "bar"]

    def test_main_return_value_passed_through(self):
        def main():
            return 42

        rc = safe_main(main, argv=["--foo"])
        assert rc == 42

    def test_main_returning_none_yields_zero(self):
        def main():
            return None

        rc = safe_main(main, argv=["--foo"])
        assert rc == 0

    def test_main_returning_non_int_yields_zero(self):
        def main():
            return "ignored"

        rc = safe_main(main, argv=["--foo"])
        assert rc == 0


class TestRejection:
    def test_rejected_argv_does_not_call_main(self, argv_rejected):
        called = []

        def main():
            called.append(True)
            return 0

        rc = safe_main(main, report_rejections=False)
        assert rc == 2
        assert called == []

    def test_rejection_writes_to_stderr_by_default(self, argv_rejected, capsys):
        def main():
            return 0

        rc = safe_main(main)
        captured = capsys.readouterr()
        assert rc == 2
        assert "rejected argv[0] (single-dash-option)" in captured.err
        assert "'-X'" in captured.err

    def test_report_rejections_false_silences_stderr(
        self, argv_rejected, capsys
    ):
        def main():
            return 0

        rc = safe_main(main, report_rejections=False)
        captured = capsys.readouterr()
        assert rc == 2
        assert captured.err == ""


class TestEnvScrub:
    def test_dangerous_env_vars_are_removed(self, monkeypatch):
        # Seed every dangerous var with a sentinel value.
        for name in DANGEROUS_PYTHON_ENV_VARS:
            monkeypatch.setenv(name, f"/tmp/evil/{name}")

        def main():
            # After safe_main, none of these should be set.
            for name in DANGEROUS_PYTHON_ENV_VARS:
                assert name not in os.environ, (
                    f"{name} should have been scrubbed"
                )
            return 0

        rc = safe_main(main, argv=["--foo"])
        assert rc == 0

    def test_unrelated_env_vars_preserved(self, monkeypatch):
        monkeypatch.setenv("ZOIDOFFICE_TEST_VAR", "keepme")
        monkeypatch.setenv("PYTHONSTARTUP", "/tmp/evil")

        def main():
            assert os.environ.get("ZOIDOFFICE_TEST_VAR") == "keepme"
            return 0

        rc = safe_main(main, argv=["--foo"])
        assert rc == 0

    def test_env_scrub_skipped_on_rejection(
        self, monkeypatch, argv_rejected
    ):
        monkeypatch.setenv("PYTHONSTARTUP", "/tmp/evil")

        def main():
            return 0

        rc = safe_main(main, report_rejections=False)
        assert rc == 2
        # Rejected path must NOT touch env vars (defense in depth).
        assert os.environ.get("PYTHONSTARTUP") == "/tmp/evil"


class TestArgvOverride:
    def test_explicit_argv_overrides_sys_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--ignored"])

        seen = []

        def main():
            seen.append(list(sys.argv[1:]))
            return 0

        rc = safe_main(main, argv=["--explicit"])
        assert rc == 0
        assert seen == [["--explicit"]]

    def test_argv_none_defaults_to_sys_argv_1(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--from-sys"])

        seen = []

        def main():
            seen.append(list(sys.argv[1:]))
            return 0

        rc = safe_main(main, argv=None)
        assert rc == 0
        assert seen == [["--from-sys"]]


class TestPolicyParity:
    """safe_main must delegate validation to sanitize_args; if the
    underlying policy changes, these tests would catch divergence."""

    def test_safe_main_rejects_what_sanitize_args_rejects(self):
        # Cross-check: every rejection from sanitize_args must also
        # be a rejection from safe_main.
        sample = [
            ["-X"],
            ["-"],
            ["--foo;bar"],
            [""],
            ["--foo", "-c"],
        ]
        for argv in sample:
            _, expected = sanitize_args(list(argv))
            seen = []

            def main():
                return 0

            rc = safe_main(main, argv=argv, report_rejections=False)
            assert rc == 2
            # Number of rejections should match (modulo `report_rejections`).
            assert seen == []
            assert expected, (
                f"sanitize_args expected to reject {argv}"
            )