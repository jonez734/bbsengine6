"""register/unregister are the names; register_module/unregister_module are aliases of them."""

from unittest.mock import patch

import pytest

from bbsengine6 import module


@pytest.mark.unit
def test_register_forwards_to_the_registry():
    with patch.object(module, "_register_module") as reg:
        module.register("demo", "demo.path", "1.0", {})
    reg.assert_called_once_with("demo", "demo.path", "1.0", {})


@pytest.mark.unit
def test_unregister_forwards_to_the_registry():
    with patch.object(module, "_unregister_module") as unreg:
        module.unregister("demo")
    unreg.assert_called_once_with("demo")


@pytest.mark.unit
def test_register_module_alias_behaves_like_register():
    with patch.object(module, "_register_module") as reg:
        module.register_module("demo", "demo.path", "1.0", {})
    reg.assert_called_once_with("demo", "demo.path", "1.0", {})


@pytest.mark.unit
def test_unregister_module_alias_behaves_like_unregister():
    with patch.object(module, "_unregister_module") as unreg:
        module.unregister_module("demo")
    unreg.assert_called_once_with("demo")


@pytest.mark.unit
def test_package_exports_both_names():
    import bbsengine6
    for name in ("register", "unregister", "register_module", "unregister_module"):
        assert hasattr(bbsengine6, name), name
        assert name in bbsengine6.__all__, name
