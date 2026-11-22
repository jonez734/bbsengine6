"""An epoch is a UTC instant (POSIX.1-2017 §4.16: seconds since the Epoch are related to Coordinated Universal Time).

datestamp(epoch) therefore formats the epoch as UTC, whatever the server TZ. Callers that want a local clock pass an
aware datetime already converted to their zone (the "explicit zone" rule); datetimes are not changed by this rule.
"""

import datetime as dt
import os
import time
import unittest
from zoneinfo import ZoneInfo

from bbsengine6.util import datestamp

FMT = "%Y-%m-%d %H:%M:%S %Z"
SERVER_ZONES = ["UTC", "Europe/London", "America/Chicago", "America/New_York", "Asia/Kolkata"]


class _TZ(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("TZ")
        self.addCleanup(self._restore)

    def _restore(self):
        if self._saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self._saved
        time.tzset()

    def server(self, zone):
        os.environ["TZ"] = zone
        time.tzset()


class TestEpochIsUTC(_TZ):
    def test_zero_is_the_utc_epoch_in_every_server_zone(self):
        for zone in SERVER_ZONES:
            with self.subTest(zone=zone):
                self.server(zone)
                self.assertEqual(datestamp(0, FMT), "1970-01-01 00:00:00 UTC")

    def test_an_int_epoch_is_utc_in_every_server_zone(self):
        epoch = int(dt.datetime(2026, 3, 8, 8, 0, 0, tzinfo=dt.timezone.utc).timestamp())
        for zone in SERVER_ZONES:
            with self.subTest(zone=zone):
                self.server(zone)
                self.assertEqual(datestamp(epoch, FMT), "2026-03-08 08:00:00 UTC")

    def test_a_float_epoch_is_utc_and_keeps_whole_seconds(self):
        self.server("America/Chicago")
        self.assertEqual(datestamp(0.0, FMT), "1970-01-01 00:00:00 UTC")
        self.assertEqual(datestamp(59.9, FMT), "1970-01-01 00:00:59 UTC")


class TestDatetimesKeepTheirZone(_TZ):
    def test_an_aware_datetime_keeps_its_own_zone(self):
        instant = dt.datetime(2026, 11, 21, 13, 49, 7, tzinfo=dt.timezone.utc)
        for zone in SERVER_ZONES:
            with self.subTest(zone=zone):
                self.server(zone)
                self.assertEqual(datestamp(instant.astimezone(ZoneInfo("America/Chicago")), FMT),
                                 "2026-11-21 07:49:07 CST")

    def test_a_naive_datetime_is_printed_without_a_zone_name(self):
        self.server("Europe/London")
        self.assertEqual(datestamp(dt.datetime(2026, 11, 21, 8, 49, 7), FMT), "2026-11-21 08:49:07 ")


if __name__ == "__main__":
    unittest.main()
