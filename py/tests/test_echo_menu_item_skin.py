"""
Regression tests for the menu item skin variables in io/echo.py.

``menu.item.enabled`` and ``menu.item.disabled`` style menu help entries. They
follow the ``listbox.item.*`` naming, with the same text colors and a gray
background for menu rows.
"""

import importlib

import pytest

pytestmark = pytest.mark.unit


def _echo_module():
    """bbsengine6.io shadows the echo submodule with the `echo` function, so
    load the submodule explicitly."""
    return importlib.import_module("bbsengine6.io.echo")


def test_menu_item_enabled_is_defined():
    skin = _echo_module()._skin
    assert skin["menu.item.enabled"] == "{white}{bggray}"


def test_menu_item_disabled_is_defined():
    skin = _echo_module()._skin
    assert skin["menu.item.disabled"] == "{darkgray}{bggray}"


def test_menu_item_disabled_is_darker_than_enabled():
    skin = _echo_module()._skin
    assert "{darkgray}" in skin["menu.item.disabled"]
    assert "{white}" in skin["menu.item.enabled"]


def test_menu_item_keys_do_not_use_old_names():
    skin = _echo_module()._skin
    assert "menuitemenabled" not in skin
    assert "menuitemdisabled" not in skin
