"""resolve_attr / check_signature / resolve_callable: a "pkg.mod:attr" string names a callable checked against a stub.

The contract check is the same one the module loader uses for access() and init() (_check_func_signature).
"""

import importlib
import sys
import types
import unittest
from unittest.mock import patch

module = importlib.import_module("bbsengine6.module")


def _stub(*, directory, title="login", header=None, fd=0, store_token=True, moniker="", **kwargs) -> tuple[str, str]:
    raise NotImplementedError


class _Base(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(module.io, "echo")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.modname = f"_resolve_{self.id().rsplit('.', 1)[-1]}"
        self.addCleanup(lambda: sys.modules.pop(self.modname, None))

    def provide(self, **attrs):
        mod = types.ModuleType(self.modname)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[self.modname] = mod
        return f"{self.modname}:"


class TestResolveAttr(_Base):
    def test_a_spec_returns_the_named_attribute(self):
        def fn(**kw):
            return None

        spec = self.provide(fn=fn) + "fn"
        self.assertIs(module.resolve_attr(spec), fn)

    def test_a_spec_without_a_colon_is_rejected(self):
        with self.assertRaises(ValueError):
            module.resolve_attr("bed.tools.authenticate.authenticate")

    def test_a_missing_module_is_rejected_with_the_spec(self):
        with self.assertRaises(ValueError) as ctx:
            module.resolve_attr("no_such_module_xyz:fn")
        self.assertIn("no_such_module_xyz:fn", str(ctx.exception))

    def test_a_missing_attribute_is_rejected_with_the_spec(self):
        spec = self.provide() + "absent"
        with self.assertRaises(ValueError) as ctx:
            module.resolve_attr(spec)
        self.assertIn("absent", str(ctx.exception))


class TestCheckSignature(_Base):
    def test_a_conforming_callable_passes(self):
        def fn(*, directory, title="login", header=None, fd=0, store_token=True, moniker="", **kwargs) -> tuple[str, str]:
            return ("", "")

        self.assertIsNone(module.check_signature(fn, _stub, name="authenticate"))

    def test_a_missing_keyword_fails_naming_the_parameter(self):
        def fn(*, directory, title="login", fd=0, **kwargs) -> tuple[str, str]:  # no 'header'? -> positional order differs
            return ("", "")

        with self.assertRaises(TypeError) as ctx:
            module.check_signature(fn, _stub, name="authenticate")
        self.assertIn("authenticate", str(ctx.exception))

    def test_a_return_that_is_not_a_tuple_at_all_fails(self):
        # The shared return rule compares the generic's origin and arguments as a set, so a plain str is rejected only
        # when it shares no member with the stub. Known gap (see the spec): a tuple of other element types is accepted.
        def fn(*, directory, title="login", header=None, fd=0, store_token=True, moniker="", **kwargs) -> int:
            return 0

        with self.assertRaises(TypeError):
            module.check_signature(fn, _stub, name="authenticate")


class TestResolveCallable(_Base):
    def test_a_good_spec_resolves_to_the_callable(self):
        def fn(*, directory, title="login", header=None, fd=0, store_token=True, moniker="", **kwargs) -> tuple[str, str]:
            return ("", "")

        spec = self.provide(fn=fn) + "fn"
        self.assertIs(module.resolve_callable(spec, _stub), fn)

    def test_a_non_callable_attribute_is_rejected_with_the_spec(self):
        spec = self.provide(fn=42) + "fn"
        with self.assertRaises(TypeError) as ctx:
            module.resolve_callable(spec, _stub)
        self.assertIn(spec, str(ctx.exception))

    def test_a_signature_mismatch_is_rejected_with_the_spec(self):
        def fn(*, directory, **kwargs) -> int:
            return 0

        spec = self.provide(fn=fn) + "fn"
        with self.assertRaises(TypeError) as ctx:
            module.resolve_callable(spec, _stub)
        self.assertIn(spec, str(ctx.exception))


class TestLoaderUsesTheSameCheck(_Base):
    def test_check_func_still_reports_the_same_result(self):
        def fn(args, **kwargs):
            return True

        mod = types.ModuleType(self.modname)
        mod.init = fn
        sys.modules[self.modname] = mod
        self.assertTrue(module.check_func(self.modname, "init", module._stub_init, silent=True))


if __name__ == "__main__":
    unittest.main()


class TestStringAnnotations(_Base):
    """A module with `from __future__ import annotations` has string annotations. The contract check must see the real
    types, or a correct callable is rejected."""

    def test_a_callable_with_string_annotations_matches_the_contract(self):
        ns = {}
        src = (
            "from __future__ import annotations\n"
            "from typing import Optional\n"
            "def fn(*, directory: str, title: str = 'login', header: Optional[str] = None, fd: int = 0,\n"
            "       store_token: bool = True, moniker: str = '', **kwargs) -> tuple[str, str]:\n"
            "    return ('', '')\n"
        )
        exec(compile(src, "<future>", "exec"), ns)
        self.assertIsNone(module.check_signature(ns["fn"], _stub, name="authenticate"))
