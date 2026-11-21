"""Pins module.check()'s current results for the init/access/buildargs/main checks.

These tests exist so a refactor of the signature checks is provably behaviour-neutral. They drive check() with small
generated modules and assert the return value and the messages it writes.
"""

import argparse
import importlib
import sys
import types
import unittest
from unittest.mock import patch

module = importlib.import_module("bbsengine6.module")


def _make_module(name, **funcs):
    mod = types.ModuleType(name)
    for attr, fn in funcs.items():
        setattr(mod, attr, fn)
    sys.modules[name] = mod
    return mod


def _good_init(args, **kwargs):
    return True


def _good_access(args, op, **kwargs):
    return True


def _good_buildargs(args, **kwargs):
    return None


def _good_main(args, **kwargs):
    return True


class _Pinned(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace(debug=False)
        self.messages = []
        patcher = patch.object(module.io, "echo", side_effect=lambda t="", *a, level=None, **k: self.messages.append((str(t), level)))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: sys.modules.pop(self.modname, None))

    def run_check(self, **funcs):
        self.modname = f"_pin_{self.id().rsplit('.', 1)[-1]}"
        _make_module(self.modname, **funcs)
        with patch.object(module, "get", side_effect=lambda mp, args, package=None: sys.modules[mp]), \
             patch.object(module, "get_require_registration", return_value=False):
            return module.check(self.args, self.modname, "run", silent=False)


class TestConformingModule(_Pinned):
    def test_a_conforming_module_passes(self):
        result = self.run_check(init=_good_init, access=_good_access, buildargs=_good_buildargs, main=_good_main)
        self.assertIs(result, True, self.messages)


class TestMissingAndNotCallable(_Pinned):
    def test_missing_init_fails(self):
        result = self.run_check(access=_good_access, buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)

    def test_init_that_is_not_callable_fails_with_a_message(self):
        result = self.run_check(init=42, access=_good_access, buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)
        self.assertIn("init function is not callable", [t for t, _ in self.messages])

    def test_missing_access_fails(self):
        result = self.run_check(init=_good_init, buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)

    def test_access_that_is_not_callable_fails_with_a_message(self):
        result = self.run_check(init=_good_init, access="nope", buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)
        self.assertIn("no callable access function", [t for t, _ in self.messages])

    def test_missing_buildargs_fails_with_a_message(self):
        result = self.run_check(init=_good_init, access=_good_access, main=_good_main)
        self.assertFalse(result)
        self.assertIn("no buildargs function found (required)", [t for t, _ in self.messages])

    def test_missing_main_fails_with_a_message(self):
        result = self.run_check(init=_good_init, access=_good_access, buildargs=_good_buildargs)
        self.assertFalse(result)
        self.assertIn("main function not found", [t for t, _ in self.messages])


class TestSignatureMismatch(_Pinned):
    def test_an_init_with_the_wrong_first_parameter_name_fails(self):
        def bad_init(argz, **kwargs):
            return True

        result = self.run_check(init=bad_init, access=_good_access, buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)
        self.assertIn("init() signature invalid", [t for t, _ in self.messages])

    def test_a_main_with_a_default_on_args_fails(self):
        def bad_main(args=None, **kwargs):
            return True

        result = self.run_check(init=_good_init, access=_good_access, buildargs=_good_buildargs, main=bad_main)
        self.assertFalse(result)
        self.assertIn("main() signature invalid", [t for t, _ in self.messages])

    def test_access_that_rejects_the_op_fails_with_an_expected_and_found_message(self):
        def bad_access(args, op_name, **kwargs):
            return True

        result = self.run_check(init=_good_init, access=bad_access, buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)
        texts = [t for t, _ in self.messages]
        self.assertTrue(any(t.startswith("access() signature mismatch") for t in texts), texts)


class TestAccessGate(_Pinned):
    def test_access_returning_false_fails_before_the_signature_checks(self):
        result = self.run_check(init=_good_init, access=lambda args, op, **k: False,
                                buildargs=_good_buildargs, main=_good_main)
        self.assertFalse(result)
        self.assertIn("access check failed", [t for t, _ in self.messages])


if __name__ == "__main__":
    unittest.main()
