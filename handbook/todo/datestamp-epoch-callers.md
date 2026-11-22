# datestamp: epoch callers to check after the UTC change

`datestamp(epoch)` now formats a Unix epoch (int, float, numeric string) as **UTC** in every server zone, per POSIX.1-2017
§4.16. A `DateTime` keeps its own zone, as before. This note lists the callers that could be affected. Nothing outside
bbsengine6 was changed.

## Not affected (import a different bbsengine, or pass aware datetimes)

- `vulcan/vulcan.py`: imports `bbsengine4`, not `bbsengine6`. Its `dateapprovedepoch` / `datepostedepoch` are epochs, so
  when `vulcan` is moved to bbsengine6 these will become UTC. Check then.
- `soctools/soctools.py`: imports the bare `bbsengine` package (v4/v5).
- `bbsengine5/` (`py/engine.py`, `py/bbsengine5.py`): imports `bbsengine5`.

## Imports bbsengine6, passes timestamptz columns (aware datetimes; zone kept)

- `socrates/src/socrates/libsocrates.py`: `datestamp(post.get("datecreated"))`, `datestamp(datelastreply)`.
- `zoidoffice/src/zoidoffice/project/update/main.py`, `project/read/main.py`, `project/search.py`,
  `project/mon/display.py`, `invoice/generateinvoice.py`, and the other zoidoffice modules that call
  `util.datestamp(...)` on `dateentered`, `nextactiontime`, `datecreated`, `duedate`.
- `murdermotel/src/murdermotel/player.py`: `datelastplayed` (timestamptz).
- `casino`, `bed`, `letteredolive`, `zoid6`: the calls I found pass aware datetimes or explicit `tzlocal()` conversions.
  `letteredolive/src/shell/lib.py` converts before calling, so it is unaffected.

## To check at each call site

- [ ] Is the argument a `datetime` (aware or naive), or an int/float epoch? Schema columns of type `timestamptz` arrive as
      datetimes; a column that stores `time.time()` is an epoch and changes to UTC.
- [ ] Does the caller expect the local clock for an epoch? If so, it must convert with `tzlocal()` before the call.
- [ ] Naive datetimes are printed without a zone name, as before.

## Not done here

No caller was edited. Each owning project decides whether an epoch should be shown in UTC or converted to local time.
