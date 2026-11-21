"""datestamp() where a DST switch happens at local midnight, in years other than 2026.

Two kinds of switch at midnight:
  - skipped midnight: the clock jumps from 23:59:59 straight to 01:00:00, so 00:00 never occurs that day.
  - repeated midnight: the clock goes back from 00:59:59 to 00:00:00, so 00:00 occurs twice.

Instants come from the tz database (zoneinfo), checked by the scan that produced them. Each case is shown one second
either side of the switch. The times are aware datetimes, so the result does not depend on the server TZ.
"""

import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from bbsengine6.util import datestamp

FMT = "%Y-%m-%d %H:%M:%S %Z"
UTC = dt.timezone.utc


def _at(zone, instant):
    return datestamp(instant.astimezone(ZoneInfo(zone)), format=FMT)


class TestSkippedMidnight(unittest.TestCase):
    def test_havana_spring_2026_skips_midnight_on_march_8(self):
        t = dt.datetime(2026, 3, 8, 5, 0, 0, tzinfo=UTC)
        self.assertEqual(_at("America/Havana", t - dt.timedelta(seconds=1)), "2026-03-07 23:59:59 CST")
        self.assertEqual(_at("America/Havana", t), "2026-03-08 01:00:00 CDT")

    def test_santiago_spring_2026_skips_midnight_on_september_6(self):
        t = dt.datetime(2026, 9, 6, 4, 0, 0, tzinfo=UTC)
        self.assertEqual(_at("America/Santiago", t - dt.timedelta(seconds=1)), "2026-09-05 23:59:59 -04")
        self.assertEqual(_at("America/Santiago", t), "2026-09-06 01:00:00 -03")


class TestRepeatedMidnight(unittest.TestCase):
    def test_havana_fall_2027_repeats_midnight_on_november_7(self):
        t = dt.datetime(2027, 11, 7, 5, 0, 0, tzinfo=UTC)
        self.assertEqual(_at("America/Havana", t - dt.timedelta(seconds=1)), "2027-11-07 00:59:59 CDT")
        self.assertEqual(_at("America/Havana", t), "2027-11-07 00:00:00 CST")

    def test_gaza_fall_2015_repeats_midnight_on_october_23(self):
        t = dt.datetime(2015, 10, 22, 22, 0, 0, tzinfo=UTC)
        self.assertEqual(_at("Asia/Gaza", t - dt.timedelta(seconds=1)), "2015-10-23 00:59:59 EEST")
        self.assertEqual(_at("Asia/Gaza", t), "2015-10-23 00:00:00 EET")


class TestMidnightMutant(unittest.TestCase):
    """A formatter that assumes midnight always exists or never repeats would be caught here."""

    def test_the_repeated_midnight_is_distinguished_by_its_zone_name(self):
        first = _at("America/Havana", dt.datetime(2027, 11, 7, 4, 30, 0, tzinfo=UTC))
        second = _at("America/Havana", dt.datetime(2027, 11, 7, 5, 30, 0, tzinfo=UTC))
        self.assertTrue(first.startswith("2027-11-07 00:30:00") and first.endswith("CDT"), first)
        self.assertTrue(second.startswith("2027-11-07 00:30:00") and second.endswith("CST"), second)


if __name__ == "__main__":
    unittest.main()
