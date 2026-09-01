#
# test_sanitize_args.py - unit tests for bbsengine6.util.sanitize_args.
#
# The function is pure (no I/O, no env access) so these tests do
# not require a database or any fixtures. They cover every policy
# branch documented in the sanitize_args docstring.
#

import sys

import pytest

sys.path.insert(0, "src")

from bbsengine6.util import sanitize_args

pytestmark = pytest.mark.unit


class TestEmptyAndNonString:
    def test_empty_argv_returns_empty(self):
        cleaned, rejections = sanitize_args([])
        assert cleaned == []
        assert rejections == []

    def test_empty_token_is_rejected(self):
        cleaned, rejections = sanitize_args([""])
        assert cleaned == []
        assert rejections == [(0, "", "empty")]

    @pytest.mark.parametrize("token", [b"bytes", 1, 1.5, None, ["nested"]])
    def test_non_string_token_is_rejected(self, token):
        cleaned, rejections = sanitize_args([token])
        assert cleaned == []
        assert len(rejections) == 1
        idx, observed_token, reason = rejections[0]
        assert idx == 0
        assert reason == "non-string-token"
        assert observed_token == repr(token)


class TestBareDash:
    def test_bare_dash_is_rejected(self):
        cleaned, rejections = sanitize_args(["-"])
        assert cleaned == []
        assert rejections == [(0, "-", "bare-dash")]

    def test_dash_after_valid_args(self):
        cleaned, rejections = sanitize_args(["--foo", "-", "bar"])
        assert cleaned == ["--foo", "bar"]
        assert rejections == [(1, "-", "bare-dash")]


class TestSingleDashOption:
    @pytest.mark.parametrize(
        "token",
        [
            "-X",
            "-c",
            "-E",
            "-I",
            "-O",
            "-S",
            "-B",
            "-R",
            "-V",
            "-W",
            "-s",
            "-t",
            "-v",
            "-b",
            "-d",
            "-i",
            "-u",
            "-x",
            "-OO",
            "-Xfaulthandler",
        ],
    )
    def test_single_dash_options_are_rejected(self, token):
        cleaned, rejections = sanitize_args([token])
        assert cleaned == []
        assert rejections == [(0, token, "single-dash-option")]


class TestLongOptValid:
    @pytest.mark.parametrize(
        "token",
        [
            "--foo",
            "--foo-bar",
            "--foo_bar",
            "--Foo123",
            "--projectid",
            "--a-b-c-d",
            "--profile",
            "--foo=value",
            "--foo=bar baz",
            "--foo=value with spaces",
            "--foo=--nested-looking--",
            "--foo=",
        ],
    )
    def test_long_opt_passes(self, token):
        cleaned, rejections = sanitize_args([token])
        assert cleaned == [token]
        assert rejections == []


class TestLongOptRejected:
    @pytest.mark.parametrize(
        "token",
        [
            # Embedded semicolon (shell metacharacter)
            "--foo;bar",
            # Embedded pipe
            "--foo|bar",
            # Embedded dollar (command substitution trigger)
            "--foo$bar",
            # Embedded backtick
            "--foo`bar`",
            # Embedded ampersand
            "--foo&bar",
            # Embedded redirect
            "--foo>bar",
            "--foo<bar",
        ],
    )
    def test_bad_long_opt_name_is_rejected(self, token):
        cleaned, rejections = sanitize_args([token])
        # All of these start with `--` and are caught by the
        # long-opt branch.
        assert cleaned == []
        assert len(rejections) == 1
        idx, observed_token, reason = rejections[0]
        assert idx == 0
        assert reason == "bad-long-opt-name"
        assert observed_token == token


class TestEndOfOptions:
    def test_double_dash_alone_passes(self):
        cleaned, rejections = sanitize_args(["--"])
        assert cleaned == ["--"]
        assert rejections == []

    def test_double_dash_terminates_options(self):
        # `--` is the argparse end-of-options marker; everything
        # after it is positional. Our sanitizer allows `--` through
        # but does NOT change the single-dash rejection for tokens
        # after it (argparse would treat them as positional; the
        # sanitizer still rejects them for defense in depth).
        cleaned, rejections = sanitize_args(["--foo", "--", "-X"])
        assert cleaned == ["--foo", "--"]
        assert rejections == [(2, "-X", "single-dash-option")]


class TestPositional:
    @pytest.mark.parametrize(
        "token",
        [
            "hello",
            "hello world",
            "abc123",
            "/path/to/file",
            "user@host",
            "value with ; shell chars",
            "$(injected)",
            "`backticks`",
            "|pipe|",
            "12345",
        ],
    )
    def test_positionals_pass(self, token):
        cleaned, rejections = sanitize_args([token])
        assert cleaned == [token]
        assert rejections == []


class TestMixed:
    def test_mixed_args_preserve_order(self):
        argv = ["--foo", "-X", "positional", "--bar=val", ""]
        cleaned, rejections = sanitize_args(argv)
        assert cleaned == ["--foo", "positional", "--bar=val"]
        assert rejections == [
            (1, "-X", "single-dash-option"),
            (4, "", "empty"),
        ]

    def test_mixed_args_with_bare_dash(self):
        argv = ["--foo", "-", "positional"]
        cleaned, rejections = sanitize_args(argv)
        assert cleaned == ["--foo", "positional"]
        assert rejections == [(1, "-", "bare-dash")]


class TestNulByte:
    def test_nul_byte_in_long_opt_value_is_rejected(self):
        cleaned, rejections = sanitize_args(["--foo=bar\x00baz"])
        assert cleaned == []
        assert rejections == [(0, "--foo=bar\x00baz", "nul-byte")]

    def test_nul_byte_in_positional_is_rejected(self):
        cleaned, rejections = sanitize_args(["foo\x00bar"])
        assert cleaned == []
        assert rejections == [(0, "foo\x00bar", "nul-byte")]


class TestReturnShape:
    def test_returns_tuple_of_lists(self):
        result = sanitize_args(["--foo", "bar"])
        assert isinstance(result, tuple)
        assert len(result) == 2
        cleaned, rejections = result
        assert isinstance(cleaned, list)
        assert isinstance(rejections, list)
        assert all(isinstance(t, str) for t in cleaned)
        assert all(
            isinstance(r, tuple) and len(r) == 3 for r in rejections
        )

    def test_cleaned_preserves_relative_order(self):
        argv = ["--z", "a", "--m", "b", "--a", "c"]
        cleaned, _ = sanitize_args(argv)
        assert cleaned == argv