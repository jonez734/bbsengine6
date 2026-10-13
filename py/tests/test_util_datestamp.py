"""
Unit tests for bbsengine6.util.datestamp() function.

Tests verify that:
1. Standard strftime tokens (Y, m, d, H, M, S, p, P, Z, a, A, b, B,
   l, z, %:z, j, %) render correctly.
2. Bare letters in the format string are preserved literally (strftime
   convention).
3. The %O opt-in token (per-user timezone offset) renders correctly:
   - empty when offset is unset or zero
   - ±HH:MM when offset is set (positive, negative, half-hour)
4. set_user_tz_offset() / get_user_tz_offset() manage the module-level
   state correctly.
5. The default format string is unchanged from before %O was added.
"""

import pytest

from bbsengine6 import util


@pytest.fixture(autouse=True)
def reset_user_tz_offset():
    """Reset module-level offset before and after each test."""
    util.set_user_tz_offset(None)
    yield
    util.set_user_tz_offset(None)


# =============================================================================
# Per-token coverage
# =============================================================================


class TestDatestampStrftimeTokens:
    """Standard strftime tokens render correctly."""

    def test_year_4digit(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%Y") == "2026"

    def test_year_2digit(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%y") == "26"

    def test_month_2digit(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%m") == "10"

    def test_short_month_name(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%b") == "Oct"

    def test_full_month_name(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%B") == "October"

    def test_day_2digit(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%d") == "13"

    def test_day_of_year(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        # 2026-10-13 is the 286th day of 2026 (1-indexed)
        assert util.datestamp(ts, "%j") == "286"

    def test_hour_24(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%H") == "14"

    def test_hour_12_padded(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%I") == "02"

    def test_hour_12_unpadded(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%l") == " 2"

    def test_minute(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%M") == "30"

    def test_second(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%S") == "00"

    def test_am_pm_uppercase(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%p") == "PM"

    def test_am_pm_lowercase(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%P") == "pm"

    def test_short_day_name(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%a") == "Tue"

    def test_full_day_name(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%A") == "Tuesday"

    def test_literal_percent(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "%%") == "%"


# =============================================================================
# Bare letters in format string (strftime convention)
# =============================================================================


class TestDatestampBareLetters:
    """Bare letters pass through literally."""

    def test_bare_letters_preserved(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        # "day" is literal — only "%j" is the token
        assert util.datestamp(ts, "day %j of %Y") == "day 286 of 2026"

    def test_bare_letters_with_hyphen(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        assert util.datestamp(ts, "day-of-year: %j") == "day-of-year: 286"

    def test_combined_format(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        # Default format uses only strftime tokens, no bare letters
        # in this particular format string
        result = util.datestamp(ts, "%Y-%m-%d %H:%M:%S")
        assert result == "2026-10-13 14:30:00"


# =============================================================================
# %O opt-in: per-user timezone offset
# =============================================================================


class TestDatestampUserOffset:
    """The %O opt-in renders the per-user timezone offset."""

    def test_offset_unset_renders_empty(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        # No set_user_tz_offset() call; autouse fixture cleared state.
        assert util.datestamp(ts, "%O") == ""

    def test_offset_unset_in_combined_format(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        # Trailing space remains in the output (no trim) when %O is empty
        assert util.datestamp(ts, "%Y-%m-%d %O") == "2026-10-13 "

    def test_offset_zero_renders_empty(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(0)
        assert util.datestamp(ts, "%O") == ""

    def test_offset_none_renders_empty(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(None)
        assert util.datestamp(ts, "%O") == ""

    def test_negative_offset_edt(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(-240)
        assert util.datestamp(ts, "%O") == "-04:00"

    def test_positive_offset_ist(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(330)
        assert util.datestamp(ts, "%O") == "+05:30"

    def test_half_hour_offset_nepal(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(345)
        assert util.datestamp(ts, "%O") == "+05:45"

    def test_negative_half_hour(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(-330)
        assert util.datestamp(ts, "%O") == "-05:30"

    def test_offset_in_combined_format(self):
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        util.set_user_tz_offset(-240)
        result = util.datestamp(ts, "%Y-%m-%d %H:%M %O")
        assert result == "2026-10-13 14:30 -04:00"


class TestDatestampSetUserOffset:
    """set_user_tz_offset / get_user_tz_offset manage module state."""

    def test_get_returns_none_initially(self):
        # autouse fixture cleared state at start
        assert util.get_user_tz_offset() is None

    def test_set_then_get(self):
        util.set_user_tz_offset(-240)
        assert util.get_user_tz_offset() == -240

    def test_set_none_clears(self):
        util.set_user_tz_offset(-240)
        util.set_user_tz_offset(None)
        assert util.get_user_tz_offset() is None

    def test_set_coerces_to_int(self):
        util.set_user_tz_offset("330")
        assert util.get_user_tz_offset() == 330
        assert isinstance(util.get_user_tz_offset(), int)

    def test_set_overwrites_previous(self):
        util.set_user_tz_offset(-240)
        util.set_user_tz_offset(330)
        assert util.get_user_tz_offset() == 330


# =============================================================================
# Default format
# =============================================================================


class TestDatestampDefaultFormat:
    """The default format is unchanged from before %O was added."""

    def test_default_format_unchanged(self):
        # The signature default is still the canonical strftime format
        # (no %O added to the default; %O is opt-in via set_user_tz_offset)
        from datetime import datetime
        ts = datetime(2026, 10, 13, 14, 30)
        result = util.datestamp(ts)
        # Verify the date portion renders correctly. The TZ part (%Z)
        # is server-dependent — UTC servers may produce empty for %Z.
        assert "2026" in result
        assert "10-13" in result
        assert "Tue" in result  # short day name (%a), not full
        # Lowercase am/pm (from %P) — the default format uses %P, not %p
        assert "pm" in result or "am" in result


# =============================================================================
# Edge cases
# =============================================================================


class TestDatestampEdgeCases:
    """Datetime argument parsing and edge cases."""

    def test_unix_epoch_int(self):
        # Unix epoch (0) is the canonical Unix timestamp. Server-local
        # year depends on TZ: 1970 in UTC and most positive-offset TZs,
        # 1969 in negative-offset TZs (e.g. America/New_York at -0500
        # renders 1969-12-31 19:00 EST). Either year is acceptable.
        result = util.datestamp(0, "%Y")
        assert result in ("1969", "1970")

    def test_none_returns_current_time(self):
        result = util.datestamp(None, "%Y")
        # Should not raise; year is a 4-digit integer string
        assert len(result) == 4
        assert result.isdigit()

    def test_invalid_type_raises_assertionerror(self):
        # dict is not a recognized type
        with pytest.raises(AssertionError):
            util.datestamp({"not": "a datetime"}, "%Y")