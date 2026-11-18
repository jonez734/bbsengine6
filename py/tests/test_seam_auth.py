"""The seam's auth scope: the login request, its refusal codes, and their wire round-trip."""

import unittest

from bbsengine6.seam.codes import ErrorCode
from bbsengine6.seam.requests import LoginRequest, Request
from bbsengine6.seam.results import ActionResult, refusal, success
from bbsengine6.seam.wire import request_from_wire, request_to_wire, result_from_wire, result_to_wire


class TestLoginRequest(unittest.TestCase):
    def test_login_is_in_the_auth_scope(self):
        req = LoginRequest(moniker="jam", password="secret")
        self.assertEqual(req.scope, "auth")
        self.assertIsInstance(req, Request)

    def test_login_request_is_frozen(self):
        req = LoginRequest(moniker="jam", password="secret")
        with self.assertRaises(Exception):
            req.moniker = "other"

    def test_request_round_trips_on_the_wire(self):
        req = LoginRequest(moniker="jam", password="secret")
        wire = request_to_wire(req)
        back = request_from_wire(wire, {"LoginRequest": LoginRequest})
        self.assertEqual(back, req)


class TestAuthCodes(unittest.TestCase):
    def test_the_auth_refusal_codes_are_generic(self):
        self.assertEqual(ErrorCode.INVALID_CREDENTIALS.value, "invalid_credentials")
        self.assertEqual(ErrorCode.AUTH_UNAVAILABLE.value, "auth_unavailable")

    def test_a_refused_login_carries_no_token(self):
        result = refusal(ErrorCode.INVALID_CREDENTIALS.value, "invalid credentials")
        self.assertFalse(result.ok)
        self.assertNotIn("token", result.data)


class TestLoginResultWire(unittest.TestCase):
    def test_a_successful_login_round_trips_its_token(self):
        result = success({"token": "tok-abc"}, message="logged in")
        back = result_from_wire(result_to_wire(result))
        self.assertTrue(back.ok)
        self.assertEqual(back.data["token"], "tok-abc")

    def test_a_refused_login_round_trips_without_a_token(self):
        result = refusal(ErrorCode.INVALID_CREDENTIALS.value, "invalid credentials")
        back = result_from_wire(result_to_wire(result))
        self.assertFalse(back.ok)
        self.assertEqual(back.code, "invalid_credentials")
        self.assertNotIn("token", back.data)


if __name__ == "__main__":
    unittest.main()
