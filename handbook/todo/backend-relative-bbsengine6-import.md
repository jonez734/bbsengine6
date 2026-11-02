# backend relative bbsengine6 imports — remaining work

`py/src/bbsengine6/backend/objects.py` imports `from bbsengine6 import database, io`
(absolute). The rest of `backend/` is mixed: 23 modules use the absolute form and
5 use relative `from . ...` imports. Decision: keep the absolute form in `objects.py`
for now, to match the majority.

Both forms resolve to the same modules. The choice is style, not behavior.

## Open

- [ ] Pick one import style for `backend/` (absolute `from bbsengine6 import ...`, or relative `from .. import ...`)
- [ ] If relative is chosen: convert the 23 absolute `backend/` modules, one commit per module group
- [ ] If absolute is kept: convert the 5 relative `backend/` modules to absolute
- [ ] Add a lint rule or test that fails on a mixed style in `backend/`

## Done when

- [ ] Every module in `backend/` uses the chosen style
- [ ] `backend/objects.py` matches the chosen style
- [ ] The full suite passes with no import-order changes in behavior
