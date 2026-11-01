# deprecated screen shim calls — remaining work

`bbsengine6.screen` is a back-compat shim over `bbsengine6.bottombar`. Calls through it emit a
`DeprecationWarning`. The library calls are not a drop-in rename: `screen.setbottombar(left, right)`
and `bottombar.setbottombar(args, buf)` have different signatures, and `screen.setarea` delegates
to the shim's own `setbottombar`. Each call site needs review before it changes.

The test modules that call the shim on purpose are already scoped (`test_screen.py`,
`test_bottombar.py`). Their filters stay until the shim is removed.

## Library call sites

- [ ] `py/src/bbsengine6/editor.py:46`: `screen.setarea(...)` in the editor status line
- [ ] `py/src/bbsengine6/menu.py:140`: `screen.setarea(...)` in the menu position line
- [ ] `py/src/bbsengine6/menu.py:272`: `screen.setarea(...)` in the menu item line
- [ ] `py/src/bbsengine6/io/getch.py:629`: `screen.get_notification_status()`; use `bottombar._get_notification_status` with explicit args/pool
- [ ] `py/src/bbsengine6/backend/lib.py:20`: `screen.setbottombar(left, right, **kwargs)`; check the `right` argument against `bottombar.setbottombar`

## Demo and test scripts (not library code)

- [ ] `py/src/testbottombar.py:35`: `screen.setbottombar(buf, rightside, stack)`
- [ ] `py/src/testeditor.py:13`: `screen.setarea("line editor")`
- [ ] `py/src/demo_listbox_masterdetail.py:180`: `io.screen.setbottombar(left, right)`
- [ ] `py/src/io_demo_inputstring.py:9`: `io.screen.setbottombar("test", "again")`

## Done when

- [ ] No `bbsengine6.screen` or `io.screen` call remains outside `screen.py` and the two scoped test modules
- [ ] The full suite runs with no `DeprecationWarning` from `bbsengine6.screen`
- [ ] `screen.py` shim removed, or kept with a dated removal note
