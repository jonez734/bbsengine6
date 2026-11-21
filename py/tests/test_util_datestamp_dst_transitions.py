"""datestamp() across the 2026 summer/fall DST transitions for London and Dallas.

London (Europe/London) and Dallas (America/Chicago, the zone Dallas keeps) change clocks on different dates:

    London   spring forward  2026-03-29 01:00 UTC   GMT  -> BST
    Dallas   spring forward  2026-03-08 08:00 UTC   CST  -> CDT   (3 weeks earlier)
    London   fall back       2026-10-25 01:00 UTC   BST  -> GMT
    Dallas   fall back       2026-11-01 07:00 UTC   CDT  -> CST   (1 week later)

Each instant is checked one second either side of the switch, so the abbreviation and the local clock both move at
the right moment. Times are built as aware datetimes, so the result does not depend on the server's TZ. A final test
sets TZ and calls tzset(), because datestamp(0) and datestamp(None) read the server zone.
"""

import datetime as dt
import os
import time
import unittest
from zoneinfo import ZoneInfo

from bbsengine6.util import datestamp

FMT = "%Y-%m-%d %H:%M:%S %Z"
UTC = dt.timezone.utc
LONDON = ZoneInfo("Europe/London")
DALLAS = ZoneInfo("America/Chicago")


def _utc(y, mo, d, h, mi=0, s=0):
    return dt.datetime(y, mo, d, h, mi, s, tzinfo=UTC)


def _local(instant, zone):
    return datestamp(instant.astimezone(zone), format=FMT)


class TestSpringForward(unittest.TestCase):
    def test_london_springs_forward_at_0100_utc_on_march_29(self):
        before = _utc(2026, 3, 29, 0, 59, 59)
        after = _utc(2026, 3, 29, 1, 0, 0)
        self.assertEqual(_local(before, LONDON), "2026-03-29 00:59:59 GMT")
        self.assertEqual(_local(after, LONDON), "2026-03-29 02:00:00 BST")

    def test_dallas_springs_forward_at_0800_utc_on_march_8(self):
        before = _utc(2026, 3, 8, 7, 59, 59)
        after = _utc(2026, 3, 8, 8, 0, 0)
        self.assertEqual(_local(before, DALLAS), "2026-03-08 01:59:59 CST")
        self.assertEqual(_local(after, DALLAS), "2026-03-08 03:00:00 CDT")

    def test_dallas_springs_forward_three_weeks_before_london(self):
        dallas = _local(_utc(2026, 3, 8, 8, 0, 0), DALLAS)
        london_before = _local(_utc(2026, 3, 8, 8, 0, 0), LONDON)
        self.assertEqual(dallas, "2026-03-08 03:00:00 CDT")
        self.assertEqual(london_before, "2026-03-08 08:00:00 GMT")


class TestFallBack(unittest.TestCase):
    def test_london_falls_back_at_0100_utc_on_october_25(self):
        before = _utc(2026, 10, 25, 0, 59, 59)
        after = _utc(2026, 10, 25, 1, 0, 0)
        self.assertEqual(_local(before, LONDON), "2026-10-25 01:59:59 BST")
        self.assertEqual(_local(after, LONDON), "2026-10-25 01:00:00 GMT")

    def test_dallas_falls_back_at_0700_utc_on_november_1(self):
        before = _utc(2026, 11, 1, 6, 59, 59)
        after = _utc(2026, 11, 1, 7, 0, 0)
        self.assertEqual(_local(before, DALLAS), "2026-11-01 01:59:59 CDT")
        self.assertEqual(_local(after, DALLAS), "2026-11-01 01:00:00 CST")

    def test_dallas_falls_back_a_week_after_london(self):
        dallas = _local(_utc(2026, 10, 25, 1, 0, 0), DALLAS)
        london = _local(_utc(2026, 10, 25, 1, 0, 0), LONDON)
        self.assertEqual(london, "2026-10-25 01:00:00 GMT")
        self.assertEqual(dallas, "2026-10-24 20:00:00 CDT")


class TestTheGapBetweenThemIsTheSpecCase(unittest.TestCase):
    """The offset between London and Dallas is 6 hours in winter and summer, but not in the weeks between the switches."""

    def _offset_hours(self, instant):
        l = instant.astimezone(LONDON).utcoffset().total_seconds() / 3600
        d = instant.astimezone(DALLAS).utcoffset().total_seconds() / 3600
        return l - d

    def test_the_offset_is_six_hours_in_winter(self):
        self.assertEqual(self._offset_hours(_utc(2026, 1, 15, 12)), 6.0)

    def test_the_offset_is_five_hours_between_march_8_and_march_29(self):
        self.assertEqual(self._offset_hours(_utc(2026, 3, 15, 12)), 5.0)

    def test_the_offset_is_six_hours_after_march_29_when_both_are_on_summer_time(self):
        self.assertEqual(self._offset_hours(_utc(2026, 4, 15, 12)), 6.0)

    def test_the_offset_is_five_hours_after_london_falls_back_while_dallas_is_still_on_cdt(self):
        self.assertEqual(self._offset_hours(_utc(2026, 10, 28, 12)), 5.0)

    def test_the_offset_is_six_hours_in_november_after_both_switches(self):
        self.assertEqual(self._offset_hours(_utc(2026, 11, 15, 12)), 6.0)


class TestServerTimezone(unittest.TestCase):
    """datestamp(epoch) reads the server TZ, so the transition is checked through TZ as well."""

    def setUp(self):
        self._saved = os.environ.get("TZ")
        self.addCleanup(self._restore)

    def _restore(self):
        if self._saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self._saved
        time.tzset()

    def test_datestamp_of_an_epoch_across_the_dallas_switch_follows_tz(self):
        epoch = _utc(2026, 3, 8, 8, 0, 0).timestamp()
        os.environ["TZ"] = "America/Chicago"
        time.tzset()
        self.assertEqual(datestamp(epoch, format=FMT), "2026-03-08 03:00:00 CDT")
        os.environ["TZ"] = "Europe/London"
        time.tzset()
        self.assertEqual(datestamp(epoch, format=FMT), "2026-03-08 08:00:00 GMT")


if __name__ == "__main__":
    unittest.main()
